from __future__ import annotations

from typing import Any

from celery import shared_task
import structlog

from app.scoring.formula import calculate_final_score, confidence_for_sources, grade_for_score
from app.scoring.versioning import score_metadata
from app.services.pipeline_state import emit_event, update_state

logger = structlog.get_logger(__name__)

BRAND_SAFETY_KEYWORDS = {
    "hate_speech": {"hate", "slur", "racist"},
    "misinformation": {"fake cure", "hoax", "conspiracy", "misinformation"},
    "scam": {"get rich quick", "guaranteed profit", "ponzi", "scam"},
    "adult": {"explicit", "nsfw", "adult content"},
    "violence": {"violent", "weapon", "bloodshed"},
}


def _risk_flags(text: str) -> tuple[dict[str, bool], list[str]]:
    lowered = text.lower()
    risks: dict[str, bool] = {}
    reasons: list[str] = []

    for risk_name, keywords in BRAND_SAFETY_KEYWORDS.items():
        matched = sorted(keyword for keyword in keywords if keyword in lowered)
        risks[risk_name] = bool(matched)
        if matched:
            reasons.append(f"{risk_name} matched keyword(s): {', '.join(matched)}")

    if not reasons:
        reasons.append("No deterministic brand-safety keywords matched.")

    return risks, reasons


def _source_count(sub_scores: dict[str, Any]) -> int:
    raw_count = sub_scores.get("data_source_count", sub_scores.get("source_count", 0))
    try:
        return max(0, int(raw_count))
    except (TypeError, ValueError):
        return 0


@shared_task(name="app.tasks.score.classify_brand_safety", bind=True)
def classify_brand_safety(self, campaign_id: str, content: dict) -> dict:
    """Keyword blocklist Pass 1 -> LLM Pass 2 classification handled by ai_agent_services.
    Returns {risks: {hate_speech, misinformation, scam, ...}, reasons[], source_url}."""
    text = " ".join(
        str(value)
        for value in (
            content.get("title", ""),
            content.get("content", ""),
            content.get("snippet", ""),
        )
    )
    risks, reasons = _risk_flags(text)
    result = {
        "risks": risks,
        "reasons": reasons,
        "source_url": content.get("url") or content.get("source_url", ""),
    }
    update_state(campaign_id, phase="score", brand_safety_checked=True)
    logger.info(
        "brand_safety_classified",
        campaign_id=campaign_id,
        source_url=result["source_url"],
        risk_count=sum(1 for flagged in risks.values() if flagged),
    )
    return result


@shared_task(name="app.tasks.score.score_influencer", bind=True)
def score_influencer(self, campaign_id: str, influencer_id: str, sub_scores: dict) -> dict:
    """Normalize sub-scores -> weighted final score -> grade handled by scoring_service.
    Returns {final_score, grade, confidence, score_version, computed_at}."""
    data_source_count = _source_count(sub_scores)
    raw_score, normalized_sub_scores = calculate_final_score(sub_scores)
    confidence, final_score = confidence_for_sources(data_source_count, raw_score)
    result = {
        "influencer_id": influencer_id,
        "final_score": final_score,
        "grade": grade_for_score(final_score),
        "confidence": confidence,
        "sub_scores": normalized_sub_scores,
        **score_metadata(data_source_count),
    }
    update_state(campaign_id, phase="score", last_scored_influencer=influencer_id, last_score=final_score)
    emit_event(
        campaign_id,
        "score.calculated",
        {
            "influencer_id": influencer_id,
            "grade": result["grade"],
            "confidence": confidence,
        },
    )
    logger.info(
        "influencer_scored",
        campaign_id=campaign_id,
        influencer_id=influencer_id,
        final_score=final_score,
        grade=result["grade"],
        confidence=confidence,
    )
    return result
