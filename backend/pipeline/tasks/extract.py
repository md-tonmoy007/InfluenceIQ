"""Extraction-phase Celery tasks."""

from __future__ import annotations

import json
import logging
import os
import re
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy.exc import IntegrityError

from backend.core.celery.app import celery_app
from backend.core.database import models
from backend.pipeline.events import (
    IdentityAmbiguous,
    IdentityResolved,
    InfluencersNone,
)
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

_PLATFORM_BASE = {
    "instagram": "https://instagram.com/",
    "tiktok": "https://tiktok.com/@",
    "youtube": "https://youtube.com/@",
}


def _build_handle_extract_prompt(text: str, url: str) -> str:
    excerpt = text[:6000]
    return (
        "You are an influencer data extraction assistant. "
        "Given the following web page content, identify every social media influencer, "
        "creator, or public figure mentioned.\n\n"
        "For each one found, extract:\n"
        "  name     — their real name or display name (string)\n"
        "  handle   — their @username including the @ symbol, or null if not stated\n"
        "  platform — one of: instagram, tiktok, youtube (string). If the "
        "creator's platform is anything else — Twitter/X, Facebook, LinkedIn, "
        "etc. — omit them entirely, do not guess one of the three.\n"
        "  followers — follower/subscriber count as an integer if mentioned, else null\n\n"
        "Rules:\n"
        "- Include ONLY real people or named creator accounts\n"
        "- Do NOT include navigation text, UI elements, brand names, or generic terms\n"
        "- Do NOT invent handles that are not explicitly present in the text\n"
        "- Return ONLY a JSON array of objects. Return [] if nothing qualifies.\n\n"
        f"Source URL: {url}\n\n"
        f"Page content:\n{excerpt}"
    )


def _llm_extract_handles(content: dict) -> list[dict] | None:
    """Call the LLM to extract influencer mentions from scraped page text.

    Returns a list of raw dicts on success, None when the LLM is disabled
    or unavailable (so the caller can fall back to regex extraction).
    """
    if os.environ.get("AI_AGENT_LLM_QUERY_PLANNING", "").strip().lower() in {"", "0", "false", "no", "off"}:
        return None

    text = str(content.get("content") or "").strip()
    if not text:
        return None

    try:
        from backend.ml.models.registry import registry
        from backend.pipeline.tasks.search import (
            _query_model_override,
            _run_predict,
            _strip_code_fence,
        )

        reg = registry()
        llm_backend = reg.get(reg.resolve_name("llm"))
        if llm_backend is None or not hasattr(llm_backend, "predict_text"):
            return None

        prompt = _build_handle_extract_prompt(text, str(content.get("url") or ""))
        raw = _run_predict(
            llm_backend.predict_text(
                prompt, max_tokens=4096, temperature=0.1, model=_query_model_override()
            )
        )
        if not raw or str(raw).startswith("[stub:"):
            return None

        cleaned = _strip_code_fence(raw)
        try:
            items = json.loads(cleaned)
        except json.JSONDecodeError:
            # Output was truncated mid-JSON — salvage complete objects by
            # finding the last complete '}' before closing the array.
            truncated = cleaned.rstrip().rstrip(",")
            try:
                items = json.loads(truncated + "]")
            except json.JSONDecodeError:
                # Truncation mid-object: find the last complete object boundary.
                last_brace = truncated.rfind("}")
                if last_brace > 0:
                    try:
                        items = json.loads(truncated[: last_brace + 1] + "]")
                    except json.JSONDecodeError:
                        log.warning("llm_extract_handles: could not recover truncated JSON for %s", content.get("url"))
                        return None
                else:
                    log.warning("llm_extract_handles: could not recover truncated JSON for %s", content.get("url"))
                    return None

        if not isinstance(items, list):
            return None

        valid = [
            item for item in items
            if isinstance(item, dict) and (item.get("handle") or item.get("name"))
        ]
        log.info("llm_extract_handles found=%d url=%s", len(valid), content.get("url"))
        return valid
    except Exception:
        log.exception("_llm_extract_handles failed for %s", content.get("url"))
        return None


def _normalize_llm_mentions(items: list[dict], source_url: str) -> list[dict]:
    """Convert raw LLM extraction output into the mention dict shape the pipeline expects."""
    mentions = []
    for item in items:
        name = str(item.get("name") or "").strip()
        raw_handle = str(item.get("handle") or "").strip()
        handle = ("@" + raw_handle.lstrip("@")) if raw_handle else ""
        platform = str(item.get("platform") or "instagram").lower().strip()
        followers = item.get("followers")

        username = handle.lstrip("@") if handle else re.sub(r"\s+", "", name.lower())
        base = _PLATFORM_BASE.get(platform)
        profile_url = f"{base}{username}" if (username and base) else ""

        from backend.pipeline.extraction.handles import is_profile_url

        if profile_url and not is_profile_url(profile_url):
            profile_url = ""
        platforms = {platform: profile_url} if profile_url else {}
        evidence = sum(bool(v) for v in (name, handle, platforms))
        mentions.append({
            "mention_id": str(uuid5(NAMESPACE_URL, f"{source_url}|{name}|{handle}")),
            "name": name or handle,
            "handle": handle or None,
            "platform": platform,
            "profile_url": profile_url or None,
            "platforms": platforms,
            "profile_urls": [profile_url] if profile_url else [],
            "credentials": [],
            "professional_titles": [],
            "authority_mentions": [],
            "emails": [],
            "phones": [],
            "websites": [],
            "addresses": [],
            "contact_info_enabled": False,
            "source_url": source_url,
            "context": "",
            "followers": followers,
            "extraction_confidence": round(min(0.95, 0.55 + 0.1 * evidence), 2),
        })
    return mentions


def _build_profile_verify_prompt(candidates: list[dict], page_url: str, text: str) -> str:
    excerpt = text[:4000]
    listing = "\n".join(
        f"{i}. platform={c['platform']} url={c['url']} "
        f"associated_name={c.get('name') or '(unknown)'}"
        for i, c in enumerate(candidates)
    )
    return (
        "You are verifying social media links extracted from a scraped web "
        "page. For each numbered candidate below, decide whether the URL is "
        "genuinely that creator's/influencer's own YouTube, TikTok, or "
        "Instagram profile page — as opposed to a brand/sponsor account, an "
        "unrelated person's profile, a placeholder/example handle, or a link "
        "that merely appears near the name coincidentally.\n\n"
        f"Source page: {page_url}\n\n"
        f"Page excerpt:\n{excerpt}\n\n"
        f"Candidates:\n{listing}\n\n"
        "Return ONLY a JSON array of the integer indices (from the list "
        "above) that are genuine creator profile links. Return [] if none "
        "qualify. Do not include an index for a URL you are not confident "
        "about."
    )


def _verify_profile_mentions_llm(mentions: list[dict], content: dict) -> list[dict]:
    """Drop platform links the LLM can't confirm are the creator's own profile.

    Fails open to the structural filter already applied upstream
    (``is_profile_url``): when the flag is off, the LLM backend is
    unavailable, or the call errors, *mentions* is returned unchanged. Only
    a successful LLM verdict removes a link — this never adds one back that
    structural filtering already rejected.
    """
    if os.environ.get("AI_AGENT_LLM_PROFILE_VERIFY", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return mentions

    candidates: list[dict] = []
    for m_idx, mention in enumerate(mentions):
        for platform, url in (mention.get("platforms") or {}).items():
            if isinstance(url, str) and url.startswith("http"):
                candidates.append({"mention_idx": m_idx, "platform": platform, "url": url, "name": mention.get("name")})
    if not candidates:
        return mentions

    try:
        from backend.ml.models.registry import registry
        from backend.pipeline.tasks.search import (
            _query_model_override,
            _run_predict,
            _strip_code_fence,
        )

        reg = registry()
        llm_backend = reg.get(reg.resolve_name("llm"))
        if llm_backend is None or not hasattr(llm_backend, "predict_text"):
            return mentions

        prompt = _build_profile_verify_prompt(candidates, str(content.get("url") or ""), str(content.get("content") or ""))
        text = _run_predict(
            llm_backend.predict_text(prompt, max_tokens=512, temperature=0.0, model=_query_model_override())
        )
        if not text or text.startswith("[stub:"):
            return mentions

        verified_indices = set(json.loads(_strip_code_fence(text)))
    except Exception:
        log.exception("_verify_profile_mentions_llm failed for %s", content.get("url"))
        return mentions

    rejected = [c for i, c in enumerate(candidates) if i not in verified_indices]
    if not rejected:
        return mentions

    log.info("profile_verify rejected=%d of %d candidates url=%s", len(rejected), len(candidates), content.get("url"))
    for candidate in rejected:
        mention = mentions[candidate["mention_idx"]]
        mention["platforms"] = {k: v for k, v in (mention.get("platforms") or {}).items() if v != candidate["url"]}
        mention["profile_urls"] = [u for u in (mention.get("profile_urls") or []) if u != candidate["url"]]
        if mention.get("profile_url") == candidate["url"]:
            mention["profile_url"] = next(iter(mention["platforms"].values()), None)
    return mentions


@celery_app.task(name="backend.pipeline.tasks.extract.extract_influencers", bind=True, max_retries=2)
def extract_influencers(self, campaign_id: str, crawl_source_id: str, content: dict) -> dict:
    """Parse a content dict into influencer mentions and score each."""
    log.info("extract_influencers campaign_id=%s crawl_source_id=%s", campaign_id, crawl_source_id)
    try:
        source_url = str(content.get("url") or "")
        llm_items = _llm_extract_handles(content)
        if llm_items is not None:
            mentions = _normalize_llm_mentions(llm_items, source_url)
        else:
            mentions = extract_influencer_mentions(content)
        mentions = _verify_profile_mentions_llm(mentions, content)
    except Exception as exc:
        log.exception("influencer extraction failed: %s", exc)
        with db_session() as session:
            refresh_campaign_status(session, campaign_id)
        publish_event(
            campaign_id,
            "extract.failed",
            crawl_source_id=crawl_source_id,
            url=content.get("url"),
            error=str(exc),
        )
        return {"crawl_source_id": crawl_source_id, "status": "failed", "error": str(exc)}

    if not mentions:
        # This can be the last outstanding source for the campaign (e.g. a
        # PDF/page with no influencer mentions) — without refreshing status
        # here, refresh_campaign_status is never called again and the
        # campaign is stuck at "running" forever.
        with db_session() as session:
            refresh_campaign_status(session, campaign_id)
        publish_event(
            campaign_id,
            "influencers.none",
            **InfluencersNone(
                campaign_id=campaign_id,
                crawl_source_id=crawl_source_id,
                url=content.get("url"),
            ).to_payload(),
        )
        return {"crawl_source_id": crawl_source_id, "status": "no_mentions"}

    new_influencer_ids: list[str] = []
    all_influencer_ids: list[str] = []
    with db_session() as session:
        crawl_source = session.get(models.CrawlSource, crawl_source_id)
        if crawl_source is None:
            return {"crawl_source_id": crawl_source_id, "status": "missing"}

        pending_influencers: dict[UUID, models.Influencer] = {}
        for mention in mentions:
            canonical = canonicalize_candidate(mention)
            influencer_id = canonical["influencer_id"]
            try:
                influencer_uuid = UUID(influencer_id)
            except (TypeError, ValueError):
                influencer_uuid = uuid4()

            influencer = session.get(models.Influencer, influencer_uuid)
            if influencer is None:
                influencer = pending_influencers.get(influencer_uuid)
            if influencer is None:
                new_inf = models.Influencer(
                    id=influencer_uuid,
                    canonical_name=canonical.get("canonical_name") or mention.get("name") or "Unknown",
                    platforms=canonical.get("platforms") or {},
                    credentials=canonical.get("credentials") or [],
                    mentions=[mention],
                )
                try:
                    with session.begin_nested():
                        session.add(new_inf)
                        session.flush()
                    influencer = new_inf
                    pending_influencers[influencer_uuid] = influencer
                    new_influencer_ids.append(str(influencer_uuid))
                except IntegrityError:
                    # Concurrent task inserted the same deterministic UUID — reload and merge
                    session.expire_all()
                    influencer = session.get(models.Influencer, influencer_uuid)
                    if influencer is None:
                        log.warning("extract_influencers: lost race on influencer %s, skipping", influencer_uuid)
                        continue
                    pending_influencers[influencer_uuid] = influencer
                    existing_mentions = list(influencer.mentions or [])
                    existing_mentions.append(mention)
                    influencer.mentions = existing_mentions
                    if canonical.get("platforms"):
                        influencer.platforms = {**(influencer.platforms or {}), **canonical.get("platforms")}
                    if canonical.get("credentials"):
                        influencer.credentials = list(
                            dict.fromkeys([*(influencer.credentials or []), *(canonical.get("credentials") or [])])
                        )
                    _persist_credentials(
                        session,
                        influencer_uuid,
                        list(influencer.credentials or []),
                        source_url=str(content.get("url") or crawl_source.url),
                        crawl_source_id=crawl_source.id,
                    )
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
                _persist_credentials(
                    session,
                    influencer_uuid,
                    list(influencer.credentials or []),
                    source_url=str(content.get("url") or crawl_source.url),
                    crawl_source_id=crawl_source.id,
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

    for influencer_id in dict.fromkeys(all_influencer_ids):
        from backend.pipeline.tasks.enrich import enrich_influencer_platforms_task

        enrich_influencer_platforms_task.delay(campaign_id, influencer_id)

    return {
        "crawl_source_id": crawl_source_id,
        "mentions": len(mentions),
        "new_influencers": new_influencer_ids,
        "influencers": all_influencer_ids,
    }


@celery_app.task(name="backend.pipeline.tasks.extract.resolve_identity_cluster", bind=True, max_retries=2)
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

    merge_count = 0
    from sqlalchemy.exc import IntegrityError

    from backend.pipeline.identity.persistence import apply_merge

    for merge_event in result.get("merge_events", []):
        try:
            canonical_id = UUID(str(merge_event.get("canonical_id")))
            merged_id = UUID(str(merge_event.get("merged_influencer_id")))
        except (TypeError, ValueError):
            continue
        try:
            with db_session() as merge_session:
                apply_merge(
                    merge_session,
                    campaign_id=campaign_uuid,
                    canonical_id=canonical_id,
                    merged_id=merged_id,
                    confidence=float(merge_event.get("confidence", 0.85)),
                    merge_strategy=str(merge_event.get("strategy", "cluster")),
                    reason=str(merge_event.get("reason", "auto_merge")),
                )
        except (IntegrityError, Exception) as exc:
            log.warning("apply_merge skipped canonical=%s merged=%s: %s", canonical_id, merged_id, exc)
            continue
        merge_count += 1

    ambiguous_pairs = result.get("ambiguous_pairs", [])

    # Emit identity.ambiguous events for pairs below auto-merge threshold
    use_llm = _llm_enabled()
    for pair in ambiguous_pairs:
        conf = float(pair.get("confidence", 0))
        if conf < AUTO_MERGE_THRESHOLD:
            publish_event(
                campaign_id,
                "identity.ambiguous",
                **IdentityAmbiguous(
                    campaign_id=campaign_id,
                    candidate_a=_candidate_preview(pair.get("candidate_a", {})),
                    candidate_b=_candidate_preview(pair.get("candidate_b", {})),
                    confidence=round(conf, 4),
                    reason=str(pair.get("reason", "")),
                ).to_payload(),
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


@celery_app.task(name="backend.pipeline.tasks.extract.resolve_identity_llm", bind=True, max_retries=2)
def resolve_identity_llm(self, campaign_id: str, candidate_a: dict, candidate_b: dict) -> dict:
    """Reconcile two candidate mentions, optionally via LLM."""
    log.info("resolve_identity_llm campaign_id=%s", campaign_id)
    decision = resolve_candidates(candidate_a, candidate_b)
    requires_llm = bool(decision.get("requires_llm"))
    use_llm = requires_llm and _llm_enabled()
    publish_event(
        campaign_id,
        "identity.resolved",
        **IdentityResolved(
            campaign_id=campaign_id,
            candidate_a=_candidate_preview(candidate_a),
            candidate_b=_candidate_preview(candidate_b),
            merge=bool(decision.get("merge", False)),
            confidence=decision.get("confidence"),
            reason=str(decision.get("reason", "")),
            llm_used=use_llm,
            llm_note="LLM endpoint not configured; deterministic verdict returned" if use_llm else None,
        ).to_payload(),
    )

    # Apply the merge if the decision is to merge (this was previously missing).
    if decision.get("merge"):
        canonical_id_str = candidate_a.get("influencer_id")
        merged_id_str = candidate_b.get("influencer_id")
        if canonical_id_str and merged_id_str and canonical_id_str != merged_id_str:
            try:
                canonical_uuid = UUID(str(canonical_id_str))
                merged_uuid = UUID(str(merged_id_str))
            except (TypeError, ValueError):
                canonical_uuid = merged_uuid = None
            if canonical_uuid and merged_uuid:
                from backend.pipeline.identity.persistence import apply_merge
                try:
                    with db_session() as merge_session:
                        apply_merge(
                            merge_session,
                            campaign_id=UUID(campaign_id),
                            canonical_id=canonical_uuid,
                            merged_id=merged_uuid,
                            confidence=float(decision.get("confidence", 0.85)),
                            merge_strategy=str(decision.get("strategy", "llm")),
                            reason=str(decision.get("reason", "llm_resolution")),
                        )
                except Exception as exc:
                    log.warning(
                        "resolve_identity_llm apply_merge failed canonical=%s merged=%s: %s",
                        canonical_uuid, merged_uuid, exc,
                    )

    return decision


def _llm_enabled() -> bool:
    return os.environ.get("AI_AGENT_LLM_IDENTITY", "0").strip().lower() in {"1", "true", "yes", "on"}


def _candidate_preview(candidate: dict) -> dict:
    return {
        "name": candidate.get("name") or candidate.get("canonical_name"),
        "handle": candidate.get("handle"),
        "platforms": candidate.get("platforms") or {},
    }


def _persist_credentials(
    session,
    influencer_uuid: UUID,
    credentials: list,
    *,
    source_url: str,
    crawl_source_id: UUID,
) -> None:
    for credential in credentials:
        if isinstance(credential, dict):
            cred_type = str(credential.get("type") or "credential")
            cred_value = str(credential.get("value") or credential.get("credential_value") or "")
            claim = str(credential.get("claim") or cred_value)
        else:
            cred_type = "credential"
            cred_value = str(credential)
            claim = cred_value
        if not cred_value:
            continue
        existing = (
            session.query(models.CredentialVerification)
            .filter(
                models.CredentialVerification.influencer_id == influencer_uuid,
                models.CredentialVerification.credential_type == cred_type,
                models.CredentialVerification.credential_value == cred_value,
                models.CredentialVerification.source_url == source_url,
            )
            .first()
        )
        if existing is None:
            session.add(
                models.CredentialVerification(
                    id=uuid4(),
                    influencer_id=influencer_uuid,
                    credential_type=cred_type,
                    credential_value=cred_value,
                    source_url=source_url,
                    crawl_source_id=crawl_source_id,
                    extracted_claim=claim,
                    verifier="pipeline",
                    confidence=0.5,
                    review_state="extracted",
                )
            )


def _bump_counter(campaign_id: str, field: str, delta: int = 1) -> int:
    from backend.core.cache.pipeline_state import increment_pipeline_counter

    return increment_pipeline_counter(campaign_id, field, delta)


__all__ = [
    "extract_influencers",
    "resolve_identity_cluster",
    "resolve_identity_llm",
]
