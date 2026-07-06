"""Score-phase Celery tasks."""

from __future__ import annotations

import logging
import os
from uuid import UUID, uuid4

from backend.core.celery.app import celery_app

from backend.core.database import models
from backend.pipeline.analysis.brand_safety_blocklist import scan_brand_safety
from backend.pipeline.candidate.builder import build_influencer_candidate, persist_candidate_snapshot
from backend.pipeline.fusion.backends.ml_adapters import explain_via_llm
from backend.pipeline.fusion.weights import campaign_weights_to_trust_weights
from backend.pipeline.orchestrator.pipeline import run_role4_pipeline
from backend.pipeline.tasks._common import (
    db_session,
    mark_campaign_failed,
    publish_event,
    refresh_campaign_status,
    set_phase,
)

log = logging.getLogger(__name__)


@celery_app.task(name="backend.pipeline.tasks.score.score_influencer", bind=True, max_retries=2)
def score_influencer(self, campaign_id: str, influencer_id: str) -> dict:
    """Run the role-5 pipeline for a single influencer and persist the score."""
    log.info("score_influencer campaign_id=%s influencer_id=%s", campaign_id, influencer_id)
    try:
        influencer_uuid = UUID(influencer_id)
        campaign_uuid = UUID(campaign_id)
    except (TypeError, ValueError) as exc:
        log.warning("Invalid ids campaign=%s influencer=%s: %s", campaign_id, influencer_id, exc)
        return {"influencer_id": influencer_id, "status": "invalid_id"}

    with db_session() as session:
        influencer = session.get(models.Influencer, influencer_uuid)
        if influencer is None:
            return {"influencer_id": influencer_id, "status": "missing"}
        canonical_name = influencer.canonical_name
        campaign = session.get(models.Campaign, campaign_uuid)
        candidate = build_influencer_candidate(session, influencer_uuid, campaign_uuid)
        sources_for_event = _sources_summary(session, influencer_uuid, campaign_uuid)
        campaign_context = _campaign_context(campaign)
        snapshot = persist_candidate_snapshot(session, campaign_uuid, influencer_uuid, candidate)
        snapshot_id = snapshot.id

    try:
        result = run_role4_pipeline(candidate, campaign=campaign_context)
    except Exception as exc:
        log.exception("run_role4_pipeline failed for %s: %s", influencer_id, exc)
        with db_session() as session:
            mark_campaign_failed(session, campaign_id, str(exc))
        return {"influencer_id": influencer_id, "status": "failed", "error": str(exc)}

    sub_scores = result.sub_scores
    signal_scores = result.signal_scores or {}
    risk_score = result.risk_score or {}
    detection = result.detection or {}

    # Optional LLM explanation enrichment
    llm_explanation = explain_via_llm(
        influencer_id,
        factors={k: float(v) for k, v in sub_scores.items() if isinstance(v, (int, float))},
        evidence_ids=list(result.source_urls),
    )
    if llm_explanation:
        result.score_event["explanation"] = llm_explanation

    with db_session() as session:
        existing_current = (
            session.query(models.InfluencerScore)
            .filter(
                models.InfluencerScore.influencer_id == influencer_uuid,
                models.InfluencerScore.campaign_id == campaign_uuid,
                models.InfluencerScore.is_current.is_(True),
            )
            .first()
        )
        score_row = models.InfluencerScore(
            id=uuid4(),
            influencer_id=influencer_uuid,
            campaign_id=campaign_uuid,
            is_current=True,
            run_trigger="initial" if existing_current is None else "rescore",
        )
        score_row.final_score = float(sub_scores.get("role4_trust_score", 0.0))
        score_row.relevance_score = float(sub_scores.get("relevance", 0.0))
        score_row.credibility_score = float(sub_scores.get("credibility", 0.0))
        score_row.engagement_score = float(sub_scores.get("engagement_quality", 0.0))
        score_row.sentiment_score = float(sub_scores.get("sentiment", 0.0))
        score_row.brand_safety_score = float(sub_scores.get("brand_safety", 0.0))
        score_row.confidence_level = result.confidence
        score_row.data_source_count = result.data_source_count
        score_row.score_version = (
            risk_score.get("model_version")
            or "Role4-InfluenceScore-v1"
        )
        score_row.signal_scores = signal_scores
        score_row.risk_category = risk_score.get("risk_category")
        score_row.detection_category = detection.get("category") if isinstance(detection, dict) else None
        score_row.positive_reasons = result.positive_reasons
        score_row.negative_reasons = result.negative_reasons
        score_row.source_provenance = sources_for_event
        score_row.scoring_weights = campaign_context.get("positive_weights")
        score_row.grade = result.grade
        score_row.trust_caps = trust_caps if isinstance(trust_caps := (result.analysis.get("trust") or {}).get("caps"), list) else []
        score_row.model_versions = signal_scores
        score_row.explanation_payload = {
            "summary": result.score_event.get("explanation"),
            "positive_reasons": result.positive_reasons,
            "negative_reasons": result.negative_reasons,
            "candidate_snapshot_id": str(snapshot_id),
        }
        session.add(score_row)
        if existing_current is not None:
            # superseded_by has no ORM relationship() (self-FK on a plain
            # column), so the unit of work has no dependency edge telling it
            # to insert score_row before this update — without the explicit
            # flush the UPDATE can be emitted first and violate the FK.
            session.flush()
            existing_current.is_current = False
            existing_current.superseded_by = score_row.id
        refresh_campaign_status(session, campaign_id)
        final_score = float(score_row.final_score or 0.0)
        score_run_id = score_row.id

    severe_flags = [
        flag for flag in (result.analysis.get("brand_safety", {}).get("flags", []) or [])
        if flag.get("severity") in {"high", "severe"}
    ]
    for flag in severe_flags[:5]:
        classify_brand_safety.delay(
            campaign_id,
            source_url=flag.get("source_url", ""),
            text=flag.get("context", ""),
            mention_label=canonical_name,
            influencer_id=influencer_id,
            score_run_id=str(score_run_id),
        )

    publish_event(
        campaign_id,
        "score.calculated",
        **result.score_event,
    )
    set_phase(campaign_id, scores_computed=_bump_counter(campaign_id, "scores_computed"))

    return {
        "influencer_id": influencer_id,
        "grade": result.grade,
        "final_score": final_score,
        "confidence": result.confidence,
    }


@celery_app.task(name="backend.pipeline.tasks.score.classify_brand_safety", bind=True, max_retries=2)
def classify_brand_safety(self, campaign_id: str, source_url: str, text: str,
                          mention_label: str = "", influencer_id: str = "",
                          score_run_id: str = "") -> dict:
    """Run a brand-safety scan and persist the flags as :class:`BrandSafetyFlag` rows."""
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
        if influencer_uuid is None:
            return {"campaign_id": campaign_id, "source_url": source_url, "flag_count": 0}
        try:
            score_uuid = UUID(score_run_id) if score_run_id else None
        except (TypeError, ValueError):
            score_uuid = None

        for flag in flags:
            row = models.BrandSafetyFlag(
                id=uuid4(),
                influencer_id=influencer_uuid,
                campaign_id=campaign_uuid,
                source_url=source_url,
                risk_type=flag.get("category", "unknown"),
                reason=flag.get("context") or flag.get("matched_keyword", ""),
                severity=flag.get("severity"),
                detection_method=flag.get("detection_method", "blocklist"),
                matched_keyword=flag.get("matched_keyword"),
                context_snippet=flag.get("context"),
                model_provider=flag.get("model_provider"),
                model_name=flag.get("model_name"),
                requires_llm_review=bool(flag.get("requires_llm_review")),
                score_run_id=score_uuid,
            )
            session.add(row)
            inserted += 1
        refresh_campaign_status(session, campaign_id)

    if _llm_enabled("AI_AGENT_LLM_BRAND_SAFETY") and scan.get("requires_llm_review"):
        log.info("brand-safety LLM path reserved (deterministic flags persisted)")

    publish_event(
        campaign_id,
        "brand_safety.flagged",
        source_url=source_url,
        mention_label=mention_label,
        influencer_id=influencer_id,
        flag_count=inserted,
        requires_llm_review=bool(scan.get("requires_llm_review")),
        sample_flags=[{
            "category": f.get("category"),
            "severity": f.get("severity"),
            "matched_keyword": f.get("matched_keyword"),
        } for f in flags[:3]],
    )
    return {
        "campaign_id": campaign_id,
        "source_url": source_url,
        "flag_count": inserted,
        "requires_llm_review": bool(scan.get("requires_llm_review")),
    }


def _llm_enabled(env_var: str) -> bool:
    return os.environ.get(env_var, "0").strip().lower() in {"1", "true", "yes", "on"}


def _build_candidate(session, influencer: models.Influencer, campaign_uuid: UUID) -> dict:
    """Backward-compatible wrapper around the shared candidate builder."""
    return build_influencer_candidate(session, influencer.id, campaign_uuid)


def _campaign_context(campaign: models.Campaign | None) -> dict:
    if campaign is None:
        return {}
    positive_weights = campaign_weights_to_trust_weights(campaign.weights)
    brief_snapshot = campaign.brief_snapshot or {}
    return {
        "campaign_id": str(campaign.id),
        "description": campaign.search_query or "",
        "interests": list(campaign.preferred_platforms or []),
        "locations": list(brief_snapshot.get("locations") or []),
        "positive_weights": positive_weights,
    }


def _sources_summary(session, influencer_uuid: UUID, campaign_uuid: UUID) -> list[dict]:
    rows = (
        session.query(models.CrawlSourceInfluencer, models.CrawlSource)
        .join(models.CrawlSource, models.CrawlSource.id == models.CrawlSourceInfluencer.crawl_source_id)
        .filter(
            models.CrawlSourceInfluencer.influencer_id == influencer_uuid,
            models.CrawlSource.campaign_id == campaign_uuid,
        )
        .all()
    )
    if rows:
        return [
            {
                "url": source.url,
                "title": source.title,
                "status": source.status,
                "relevance_score": source.relevance_score,
                "content": source.content,
                "mention_id": link.mention_id,
                "mention": link.mention,
            }
            for link, source in rows
        ]

    legacy_rows = (
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
            "content": row.content,
        }
        for row in legacy_rows
    ]


def _bump_counter(campaign_id: str, field: str, delta: int = 1) -> int:
    from backend.core.cache.pipeline_state import increment_pipeline_counter

    return increment_pipeline_counter(campaign_id, field, delta)


__all__ = ["classify_brand_safety", "score_influencer"]
