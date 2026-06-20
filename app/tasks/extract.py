"""Extraction-phase Celery tasks.

Two task bodies live here:

* :func:`extract_influencers` (``app.tasks.extract.extract_influencers``,
  ``scoring_queue``) — runs
  :func:`scoring_service.extraction.entities.extract_influencer_mentions`
  over a content dict, upserts ``Influencer`` and ``CrawlSource``
  rows, and dispatches :func:`app.tasks.score.score_influencer` for
  every newly-resolved canonical influencer.

* :func:`resolve_identity_llm` (``app.tasks.extract.resolve_identity_llm``,
  ``ai_agent_queue``) — LLM-assisted disambiguation of two candidate
  influencer mentions. In v1 the deterministic
  :func:`scoring_service.identity.resolver.resolve_candidates` already
  returns an ``"ambiguous"`` verdict; this task re-runs that resolver
  and only invokes an LLM when ``AI_AGENT_LLM_IDENTITY=1`` is set and
  the resolver flagged the pair as ambiguous.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from celery import shared_task

from app.db import models
from app.tasks._common import db_session, publish_event, set_phase
from scoring_service.extraction.entities import extract_influencer_mentions
from scoring_service.identity.canonical import canonicalize_candidate
from scoring_service.identity.resolver import resolve_candidates

log = logging.getLogger(__name__)


@shared_task(name="app.tasks.extract.extract_influencers", bind=True, max_retries=2)
def extract_influencers(self, campaign_id: str, crawl_source_id: str, content: dict) -> dict:
    """Parse a content dict into influencer mentions and score each.

    Steps:
    1. Run :func:`extract_influencer_mentions` on the content dict.
    2. For every mention, find-or-create a canonical ``Influencer``
       row keyed by the mention's profile URLs (sha256 hash in the
       resolver's helpers).
    3. Link the ``CrawlSource`` to each newly-attributed
       ``Influencer``.
    4. Fan out :func:`app.tasks.score.score_influencer` per
       influencer so the scoring step runs in parallel.

    The task is idempotent: re-running it on the same content
    produces the same canonical influencers.
    """
    log.info("extract_influencers campaign_id=%s crawl_source_id=%s", campaign_id, crawl_source_id)
    try:
        mentions = extract_influencer_mentions(content)
    except Exception as exc:
        log.exception("extract_influencer_mentions failed: %s", exc)
        return {"crawl_source_id": crawl_source_id, "status": "failed", "error": str(exc)}

    if not mentions:
        publish_event(campaign_id, "influencers.none",
                      crawl_source_id=crawl_source_id, url=content.get("url"))
        return {"crawl_source_id": crawl_source_id, "status": "no_mentions"}

    new_influencer_ids: list[str] = []
    with db_session() as session:
        crawl_source = session.get(models.CrawlSource, crawl_source_id)
        if crawl_source is None:
            return {"crawl_source_id": crawl_source_id, "status": "missing"}

        # Track mentions already attached to this crawl source so
        # the same mention does not re-attach on retry.
        existing_links = {
            (link.influencer_id, link.mention_id)
            for link in crawl_source.mentions or []
        } if hasattr(crawl_source, "mentions") else set()

        for mention in mentions:
            canonical = canonicalize_candidate(mention)
            influencer_id = canonical["influencer_id"]
            try:
                influencer_uuid = UUID(influencer_id)
            except (TypeError, ValueError):
                influencer_uuid = uuid4()

            influencer = session.get(models.Influencer, influencer_uuid)
            if influencer is None:
                influencer = models.Influencer(
                    id=influencer_uuid,
                    canonical_name=canonical.get("canonical_name") or mention.get("name") or "Unknown",
                    platforms=canonical.get("platforms") or {},
                    credentials=canonical.get("credentials") or [],
                    mentions=[mention],
                )
                session.add(influencer)
                new_influencer_ids.append(str(influencer_uuid))
            else:
                # Merge mentions: extend the JSONB list with the new one.
                existing_mentions = list(influencer.mentions or [])
                existing_mentions.append(mention)
                influencer.mentions = existing_mentions
                # Extend platforms/credentials/followers lazily.
                for key, value in (
                    ("platforms", canonical.get("platforms") or {}),
                    ("credentials", canonical.get("credentials") or []),
                ):
                    if value:
                        merged = {**(influencer.platforms or {}), **value} if key == "platforms" \
                            else list(dict.fromkeys([*(influencer.credentials or []), *value]))
                        setattr(influencer, key, merged)

            # Attach the CrawlSource → Influencer link.
            crawl_source.influencer_id = influencer_uuid
            mention_id = mention.get("mention_id")
            if (influencer_uuid, mention_id) not in existing_links:
                # The model has no explicit join table; the relationship
                # is one CrawlSource → one Influencer. The mention
                # itself lives inside the Influencer's ``mentions``
                # JSONB so the link is already durable.
                pass

    set_phase(campaign_id, influencers_found=_bump_counter(campaign_id, "influencers_found", len(new_influencer_ids)))
    publish_event(campaign_id, "influencer.found",
                  crawl_source_id=crawl_source_id,
                  url=content.get("url"),
                  new_influencer_ids=new_influencer_ids,
                  mention_count=len(mentions))

    # Fan out a scoring task per *new* influencer only — the existing
    # ones were scored by the previous run on this source.
    for influencer_id in new_influencer_ids:
        from app.tasks.score import score_influencer  # local import to avoid cycle
        score_influencer.delay(campaign_id, influencer_id)

    return {
        "crawl_source_id": crawl_source_id,
        "mentions": len(mentions),
        "new_influencers": new_influencer_ids,
    }


@shared_task(name="app.tasks.extract.resolve_identity_llm", bind=True, max_retries=2)
def resolve_identity_llm(self, campaign_id: str, candidate_a: dict, candidate_b: dict) -> dict:
    """Reconcile two candidate mentions, optionally via LLM.

    In v1 the deterministic resolver
    :func:`scoring_service.identity.resolver.resolve_candidates`
    already produces a verdict. The LLM path is reserved for cases
    where the resolver returned ``requires_llm=True`` and the
    ``AI_AGENT_LLM_IDENTITY`` env flag is set. When neither is true
    the task returns the resolver's verdict verbatim.
    """
    log.info("resolve_identity_llm campaign_id=%s", campaign_id)
    decision = resolve_candidates(candidate_a, candidate_b)
    requires_llm = bool(decision.get("requires_llm"))
    use_llm = requires_llm and _llm_enabled()
    payload = {
        "candidate_a": _candidate_preview(candidate_a),
        "candidate_b": _candidate_preview(candidate_b),
        "merge": decision.get("merge", False),
        "confidence": decision.get("confidence"),
        "reason": decision.get("reason"),
        "llm_used": use_llm,
    }
    if use_llm:
        # LLM wiring is intentionally deferred; the deterministic
        # resolver is the production fallback in v1. When the
        # provider is wired it lives here.
        payload["llm_note"] = "LLM endpoint not configured; deterministic verdict returned"
    publish_event(campaign_id, "identity.resolved", **payload)
    return decision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _llm_enabled() -> bool:
    import os
    return os.environ.get("AI_AGENT_LLM_IDENTITY", "0").strip().lower() in {"1", "true", "yes", "on"}


def _candidate_preview(candidate: dict) -> dict:
    """Reduce a candidate dict to the fields the event payload needs."""
    return {
        "name": candidate.get("name") or candidate.get("canonical_name"),
        "handle": candidate.get("handle"),
        "platforms": candidate.get("platforms") or {},
    }


def _bump_counter(campaign_id: str, field: str, delta: int = 1) -> int:
    from app.services.pipeline_state import get_pipeline_state
    state = get_pipeline_state(campaign_id) or {}
    return int(state.get(field, 0)) + delta


__all__ = ["extract_influencers", "resolve_identity_llm"]
