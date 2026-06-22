"""Extraction-phase Celery tasks."""

from __future__ import annotations

import logging
import os
from uuid import UUID, uuid4

from celery import shared_task

from backend.core.database import models
from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.identity.canonical import canonicalize_candidate
from backend.pipeline.identity.resolver import resolve_candidates, resolve_identity_clusters
from backend.pipeline.tasks._common import (
    db_session,
    publish_event,
    refresh_campaign_status,
    set_phase,
)

log = logging.getLogger(__name__)

AUTO_MERGE_THRESHOLD = 0.85


@shared_task(name="backend.pipeline.tasks.extract.extract_influencers", bind=True, max_retries=2)
def extract_influencers(self, campaign_id: str, crawl_source_id: str, content: dict) -> dict:
    """Parse a content dict into influencer mentions and score each."""
    log.info("extract_influencers campaign_id=%s crawl_source_id=%s", campaign_id, crawl_source_id)
    try:
        mentions = extract_influencer_mentions(content)
    except Exception as exc:
        log.exception("extract_influencer_mentions failed: %s", exc)
        return {"crawl_source_id": crawl_source_id, "status": "failed", "error": str(exc)}

    if not mentions:
        publish_event(campaign_id, "influencers.none", crawl_source_id=crawl_source_id, url=content.get("url"))
        return {"crawl_source_id": crawl_source_id, "status": "no_mentions"}

    new_influencer_ids: list[str] = []
    all_influencer_ids: list[str] = []
    with db_session() as session:
        crawl_source = session.get(models.CrawlSource, crawl_source_id)
        if crawl_source is None:
            return {"crawl_source_id": crawl_source_id, "status": "missing"}

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
                existing_mentions = list(influencer.mentions or [])
                existing_mentions.append(mention)
                influencer.mentions = existing_mentions
                if canonical.get("platforms"):
                    influencer.platforms = {**(influencer.platforms or {}), **canonical.get("platforms")}
                if canonical.get("credentials"):
                    influencer.credentials = list(
                        dict.fromkeys([*(influencer.credentials or []), *(canonical.get("credentials") or [])])
                    )

            mention_id = mention.get("mention_id")
            existing_link = (
                session.query(models.CrawlSourceInfluencer)
                .filter(
                    models.CrawlSourceInfluencer.crawl_source_id == crawl_source.id,
                    models.CrawlSourceInfluencer.influencer_id == influencer_uuid,
                    models.CrawlSourceInfluencer.mention_id == mention_id,
                )
                .first()
            )
            if existing_link is None:
                session.add(
                    models.CrawlSourceInfluencer(
                        id=uuid4(),
                        crawl_source_id=crawl_source.id,
                        influencer_id=influencer_uuid,
                        mention_id=mention_id,
                        mention=mention,
                    )
                )

            all_influencer_ids.append(str(influencer_uuid))

        if all_influencer_ids:
            try:
                crawl_source.influencer_id = UUID(all_influencer_ids[0])
            except (TypeError, ValueError):
                pass
        refresh_campaign_status(session, campaign_id)

    set_phase(campaign_id, influencers_found=_bump_counter(campaign_id, "influencers_found", len(new_influencer_ids)))
    publish_event(
        campaign_id,
        "influencer.found",
        crawl_source_id=crawl_source_id,
        url=content.get("url"),
        new_influencer_ids=new_influencer_ids,
        influencer_ids=all_influencer_ids,
        mention_count=len(mentions),
    )

    # Trigger identity cluster resolution after every extraction
    resolve_identity_cluster.delay(campaign_id)

    for influencer_id in new_influencer_ids:
        from backend.pipeline.tasks.score import score_influencer

        score_influencer.delay(campaign_id, influencer_id)

    return {
        "crawl_source_id": crawl_source_id,
        "mentions": len(mentions),
        "new_influencers": new_influencer_ids,
        "influencers": all_influencer_ids,
    }


@shared_task(name="backend.pipeline.tasks.extract.resolve_identity_cluster", bind=True, max_retries=2)
def resolve_identity_cluster(self, campaign_id: str) -> dict:
    """Campaign-wide identity cluster resolution.

    Loads all influencer records for *campaign_id*, runs
    :func:`resolve_identity_clusters`, and emits ``identity.merged``
    events for confident matches (confidence >= 0.85). Pairs below
    that threshold emit ``identity.ambiguous`` events and, when the
    ``AI_AGENT_LLM_IDENTITY`` flag is on, are dispatched to
    :func:`resolve_identity_llm`.
    """
    log.info("resolve_identity_cluster campaign_id=%s", campaign_id)
    try:
        campaign_uuid = UUID(campaign_id)
    except (TypeError, ValueError) as exc:
        log.warning("Invalid campaign_id %s: %s", campaign_id, exc)
        return {"campaign_id": campaign_id, "status": "invalid_id"}

    with db_session() as session:
        campaign = session.get(models.Campaign, campaign_uuid)
        if campaign is None:
            return {"campaign_id": campaign_id, "status": "campaign_not_found"}

        # Collect all influencers for this campaign
        influencers = (
            session.query(models.Influencer)
            .join(models.CrawlSourceInfluencer)
            .join(models.CrawlSource)
            .filter(models.CrawlSource.campaign_id == campaign_uuid)
            .distinct()
            .all()
        )
        if not influencers:
            return {"campaign_id": campaign_id, "status": "no_influencers", "influencer_count": 0}

        # Build candidate dicts from ORM rows
        candidates = []
        for inf in influencers:
            platforms = dict(inf.platforms or {})
            profile_urls = [v for v in platforms.values() if isinstance(v, str)]
            candidate = {
                "influencer_id": str(inf.id),
                "canonical_name": inf.canonical_name or "",
                "platforms": platforms,
                "profile_urls": profile_urls,
                "credentials": list(inf.credentials or []),
                "professional_titles": [],
                "mentions": list(inf.mentions or []),
            }
            candidates.append(candidate)

    # Run cluster resolution
    def _emit(cid: str, event_type: str, payload: object) -> None:
        if isinstance(payload, dict):
            publish_event(cid, event_type, **payload)

    result = resolve_identity_clusters(
        candidates,
        campaign_id=campaign_id,
        event_emitter=_emit,
    )

    merge_count = len(result.get("merge_events", []))
    ambiguous_pairs = result.get("ambiguous_pairs", [])

    # Emit identity.ambiguous events for pairs below auto-merge threshold
    use_llm = _llm_enabled()
    for pair in ambiguous_pairs:
        conf = float(pair.get("confidence", 0))
        if conf < AUTO_MERGE_THRESHOLD:
            publish_event(
                campaign_id,
                "identity.ambiguous",
                candidate_a=_candidate_preview(pair.get("candidate_a", {})),
                candidate_b=_candidate_preview(pair.get("candidate_b", {})),
                confidence=round(conf, 4),
                reason=pair.get("reason", ""),
            )
            if use_llm:
                resolve_identity_llm.delay(
                    campaign_id,
                    pair["candidate_a"],
                    pair["candidate_b"],
                )

    log.info(
        "resolve_identity_cluster campaign_id=%s merges=%d ambiguous=%d llm=%s",
        campaign_id, merge_count, len(ambiguous_pairs), use_llm,
    )
    return {
        "campaign_id": campaign_id,
        "merge_count": merge_count,
        "ambiguous_count": len(ambiguous_pairs),
        "llm_dispatched": use_llm and len(ambiguous_pairs) > 0,
    }


@shared_task(name="backend.pipeline.tasks.extract.resolve_identity_llm", bind=True, max_retries=2)
def resolve_identity_llm(self, campaign_id: str, candidate_a: dict, candidate_b: dict) -> dict:
    """Reconcile two candidate mentions, optionally via LLM."""
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
        payload["llm_note"] = "LLM endpoint not configured; deterministic verdict returned"
    publish_event(campaign_id, "identity.resolved", **payload)
    return decision


def _llm_enabled() -> bool:
    return os.environ.get("AI_AGENT_LLM_IDENTITY", "0").strip().lower() in {"1", "true", "yes", "on"}


def _candidate_preview(candidate: dict) -> dict:
    return {
        "name": candidate.get("name") or candidate.get("canonical_name"),
        "handle": candidate.get("handle"),
        "platforms": candidate.get("platforms") or {},
    }


def _bump_counter(campaign_id: str, field: str, delta: int = 1) -> int:
    from backend.core.cache.pipeline_state import get_pipeline_state

    state = get_pipeline_state(campaign_id) or {}
    return int(state.get(field, 0)) + delta


__all__ = [
    "extract_influencers",
    "resolve_identity_cluster",
    "resolve_identity_llm",
]
