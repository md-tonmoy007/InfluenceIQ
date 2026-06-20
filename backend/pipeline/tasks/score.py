"""Score-phase Celery tasks.

Two task bodies live here:

* :func:`score_influencer` (``backend.pipeline.tasks.score.score_influencer``,
  ``scoring_queue``) — assembles a role-5 candidate from the
  influencer row + its crawl sources, runs
  :func:`backend.pipeline.orchestrator.pipeline.run_role5_pipeline`,
  and persists an :class:`InfluencerScore` row.

* :func:`classify_brand_safety` (``backend.pipeline.tasks.score.classify_brand_safety``,
  ``ai_agent_queue``) — runs
  :func:`backend.pipeline.analysis.brand_safety_blocklist.scan_brand_safety`
  and persists :class:`BrandSafetyFlag` rows. The LLM path is gated
  on ``AI_AGENT_LLM_BRAND_SAFETY=1`` and is intentionally a stub
  in v1 (deterministic blocklist is the production fallback).
"""

from __future__ import annotations

import logging
import os
from uuid import UUID, uuid4

from celery import shared_task

from backend.core.database import models
from backend.pipeline.analysis.brand_safety_blocklist import scan_brand_safety
from backend.pipeline.orchestrator.pipeline import run_role5_pipeline
from backend.pipeline.tasks._common import db_session, publish_event, set_phase

log = logging.getLogger(__name__)


@shared_task(name="backend.pipeline.tasks.score.score_influencer", bind=True, max_retries=2)
def score_influencer(self, campaign_id: str, influencer_id: str) -> dict:
    """Run the role-5 pipeline for a single influencer and persist the score.

    Steps:
    1. Load the ``Influencer`` row and every ``CrawlSource`` linked
       to it via the JSONB ``mentions`` list.
    2. Assemble a candidate dict shaped for ``run_role5_pipeline``.
    3. Run the pipeline (deterministic unless ``ML_USE_*`` flags
       are set in the worker env).
    4. Persist an :class:`InfluencerScore` row and emit a
       ``score.calculated`` event.
    5. Bump the ``scores_computed`` counter in the pipeline state.
    """
    log.info("score_influencer campaign_id=%s influencer_id=%s", campaign_id, influencer_id)
    try:
        influencer_uuid = UUID(influencer_id)
    except (TypeError, ValueError) as exc:
        log.warning("Invalid influencer_id %s: %s", influencer_id, exc)
        return {"influencer_id": influencer_id, "status": "invalid_id"}

    with db_session() as session:
        influencer = session.get(models.Influencer, influencer_uuid)
        if influencer is None:
            return {"influencer_id": influencer_id, "status": "missing"}
        campaign = session.get(models.Campaign, UUID(campaign_id)) if campaign_id else None
        candidate = _build_candidate(influencer, campaign)
        sources_for_event = _sources_summary(session, influencer_uuid, UUID(campaign_id))

    try:
        result = run_role5_pipeline(candidate, campaign=_campaign_context(campaign))
    except Exception as exc:
        log.exception("run_role5_pipeline failed for %s: %s", influencer_id, exc)
        return {"influencer_id": influencer_id, "status": "failed", "error": str(exc)}

    sub_scores = result.sub_scores
    signal_scores = result.signal_scores or {}
    risk_score = result.risk_score
    detection = result.detection

    with db_session() as session:
        existing = (
            session.query(models.InfluencerScore)
            .filter(
                models.InfluencerScore.influencer_id == influencer_uuid,
                models.InfluencerScore.campaign_id == UUID(campaign_id),
            )
            .first()
        )
        score_row = existing or models.InfluencerScore(
            id=uuid4(),
            influencer_id=influencer_uuid,
            campaign_id=UUID(campaign_id),
        )
        score_row.final_score = float(sub_scores.get("role5_trust_score", 0.0))
        score_row.relevance_score = float(sub_scores.get("relevance", 0.0))
        score_row.credibility_score = float(sub_scores.get("credibility", 0.0))
        score_row.engagement_score = float(sub_scores.get("engagement_quality", 0.0))
        score_row.sentiment_score = float(sub_scores.get("sentiment", 0.0))
        score_row.brand_safety_score = float(sub_scores.get("brand_safety", 0.0))
        score_row.confidence_level = result.confidence
        score_row.data_source_count = result.data_source_count
        score_row.score_version = (risk_score or {}).get("model_version") or "v1.0"
        if existing is None:
            session.add(score_row)

    # Brand-safety flags come from the orchestrator's risk/scan. We
    # forward severe ones through the dedicated task so the event
    # log carries a brand-safety-specific payload.
    severe_flags = [
        flag for flag in (result.analysis.get("brand_safety", {}).get("flags", []) or [])
        if flag.get("severity") in {"high", "severe"}
    ]
    for flag in severe_flags[:5]:
        classify_brand_safety.delay(
            campaign_id,
            source_url=flag.get("source_url", ""),
            text=flag.get("context", ""),
            mention_label=influencer.canonical_name,
            influencer_id=influencer_id,
        )

    publish_event(campaign_id, "score.calculated",
                  influencer_id=influencer_id,
                  canonical_name=influencer.canonical_name,
                  grade=result.grade,
                  confidence=result.confidence,
                  final_score=score_row.final_score,
                  sub_scores=sub_scores,
                  signal_scores=signal_scores,
                  risk_category=(risk_score or {}).get("risk_category"),
                  detection_category=detection.get("category") if isinstance(detection, dict) else None,
                  data_source_count=result.data_source_count,
                  positive_reasons=result.positive_reasons,
                  negative_reasons=result.negative_reasons,
                  sources=sources_for_event)
    set_phase(campaign_id, scores_computed=_bump_counter(campaign_id, "scores_computed"))

    return {
        "influencer_id": influencer_id,
        "grade": result.grade,
        "final_score": score_row.final_score,
        "confidence": result.confidence,
    }


@shared_task(name="backend.pipeline.tasks.score.classify_brand_safety", bind=True, max_retries=2)
def classify_brand_safety(self, campaign_id: str, source_url: str, text: str,
                          mention_label: str = "", influencer_id: str = "") -> dict:
    """Run a brand-safety scan and persist the flags as :class:`BrandSafetyFlag` rows.

    The LLM path is reserved for when ``AI_AGENT_LLM_BRAND_SAFETY=1``
    is set; the deterministic blocklist scanner is the production
    fallback in v1.
    """
    log.info("classify_brand_safety campaign_id=%s source_url=%s", campaign_id, source_url)
    scan = scan_brand_safety(text or "", source_url=source_url)
    flags = scan.get("flags", []) or []
    if not flags:
        return {"campaign_id": campaign_id, "source_url": source_url, "flag_count": 0}

    inserted = 0
    with db_session() as session:
        try:
            campaign_uuid = UUID(campaign_id)
        except (TypeError, ValueError):
            return {"campaign_id": campaign_id, "source_url": source_url, "flag_count": 0}
        try:
            influencer_uuid = UUID(influencer_id) if influencer_id else None
        except (TypeError, ValueError):
            influencer_uuid = None

        for flag in flags:
            row = models.BrandSafetyFlag(
                id=uuid4(),
                influencer_id=influencer_uuid or uuid4(),
                campaign_id=campaign_uuid,
                source_url=source_url,
                risk_type=flag.get("category", "unknown"),
                reason=flag.get("context") or flag.get("matched_keyword", ""),
            )
            session.add(row)
            inserted += 1

    if _llm_enabled("AI_AGENT_LLM_BRAND_SAFETY") and scan.get("requires_llm_review"):
        # Reserved for the future LLM re-classification pass. The
        # deterministic flags above are the persisted source of truth.
        log.info("brand-safety LLM path reserved (deterministic flags persisted)")

    publish_event(campaign_id, "brand_safety.flagged",
                  source_url=source_url,
                  mention_label=mention_label,
                  influencer_id=influencer_id,
                  flag_count=inserted,
                  requires_llm_review=bool(scan.get("requires_llm_review")),
                  sample_flags=[{
                      "category": f.get("category"),
                      "severity": f.get("severity"),
                      "matched_keyword": f.get("matched_keyword"),
                  } for f in flags[:3]])
    return {
        "campaign_id": campaign_id,
        "source_url": source_url,
        "flag_count": inserted,
        "requires_llm_review": bool(scan.get("requires_llm_review")),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _llm_enabled(env_var: str) -> bool:
    return os.environ.get(env_var, "0").strip().lower() in {"1", "true", "yes", "on"}


def _build_candidate(influencer: models.Influencer, campaign: models.Campaign | None) -> dict:
    """Project an Influencer row into the candidate dict shape role-5 expects."""
    mentions = list(influencer.mentions or [])
    platforms = dict(influencer.platforms or {})
    profile_urls: list[str] = []
    for value in platforms.values():
        if isinstance(value, str):
            profile_urls.append(value)
    return {
        "influencer_id": str(influencer.id),
        "canonical_name": influencer.canonical_name,
        "platforms": platforms,
        "profile_urls": profile_urls,
        "credentials": list(influencer.credentials or []),
        "professional_titles": [],
        "mentions": mentions,
        "data_source_count": len({m.get("source_url") for m in mentions if m.get("source_url")}),
        "source_url": profile_urls[0] if profile_urls else "",
        "source_urls": profile_urls,
        "bio": "",
        "content": "",
        "context": "",
        "comments": [],
        "followers": 0,
        "average_engagement": 0,
        "verified": False,
    }


def _campaign_context(campaign: models.Campaign | None) -> dict:
    if campaign is None:
        return {}
    return {
        "campaign_id": str(campaign.id),
        "product": campaign.product,
        "category": campaign.niche,
        "niche": campaign.niche,
        "goal": campaign.goals or "",
        "interests": list(campaign.preferred_platforms or []),
        "target_audience": campaign.target_audience or "",
    }


def _sources_summary(session, influencer_uuid: UUID, campaign_uuid: UUID) -> list[dict]:
    """Return a compact source list for the score event payload."""
    rows = (
        session.query(models.CrawlSource)
        .filter(
            models.CrawlSource.influencer_id == influencer_uuid,
            models.CrawlSource.campaign_id == campaign_uuid,
        )
        .all()
    )
    return [
        {
            "url": row.url,
            "title": row.title,
            "status": row.status,
            "relevance_score": row.relevance_score,
        }
        for row in rows
    ]


def _bump_counter(campaign_id: str, field: str, delta: int = 1) -> int:
    from backend.core.cache.pipeline_state import get_pipeline_state
    state = get_pipeline_state(campaign_id) or {}
    return int(state.get(field, 0)) + delta


__all__ = ["classify_brand_safety", "score_influencer"]
