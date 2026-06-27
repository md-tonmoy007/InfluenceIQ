from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import models
from backend.core.database.session import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/api/influencers", tags=["influencers"])


@router.get("/{id}", response_model=dict[str, Any])
def get_influencer_profile(
    id: UUID,
    include_history: bool = Query(
        default=False,
        description="Include the most recent N campaign scores alongside the profile.",
    ),
    history_limit: int = Query(
        default=5,
        ge=1,
        le=50,
        description="How many recent score rows to return when include_history=true.",
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves canonical metadata for a specific influencer profile.

    The base response is the persistent profile; pass ``include_history=true``
    to receive a small ``score_history`` array of the most recent
    ``InfluencerScore`` rows so the frontend can show "this influencer
    has also ranked for these other campaigns" without an extra round trip.
    """
    log = logger.bind(influencer_id=str(id))
    log.info("Fetching influencer profile")

    inf = db.query(models.Influencer).filter(models.Influencer.id == id).first()
    if not inf:
        log.warning("Influencer not found")
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    response: dict[str, Any] = {
        "id": inf.id,
        "canonical_name": inf.canonical_name,
        "platforms": inf.platforms or {},
        "credentials": inf.credentials or [],
        "mentions": inf.mentions or [],
        "primary_platform": inf.primary_platform,
        "primary_handle": inf.primary_handle,
        "follower_count": inf.follower_count,
        "engagement_rate": inf.engagement_rate,
        "avg_views": inf.avg_views,
        "primary_category": inf.primary_category,
        "primary_location": inf.primary_location,
        "created_at": inf.created_at,
        "updated_at": inf.updated_at,
    }

    # Cross-campaign provenance: a small set of recent scores so the
    # frontend can show "also ranked for…" without a follow-up call.
    if include_history:
        recent_scores = (
            db.query(models.InfluencerScore)
            .filter(models.InfluencerScore.influencer_id == id)
            .order_by(models.InfluencerScore.computed_at.desc())
            .limit(history_limit)
            .all()
        )
        response["score_history"] = [
            {
                "score_id": s.id,
                "campaign_id": s.campaign_id,
                "final_score": s.final_score,
                "computed_at": s.computed_at,
                "score_version": s.score_version,
                "risk_category": s.risk_category,
                "detection_category": s.detection_category,
            }
            for s in recent_scores
        ]
        # Aggregate: how many campaigns has this influencer been scored in?
        total = (
            db.query(func.count(models.InfluencerScore.id))
            .filter(models.InfluencerScore.influencer_id == id)
            .scalar()
        )
        response["score_history_total"] = int(total or 0)

    return response


@router.get("/{id}/scores", response_model=list[dict[str, Any]])
def get_influencer_scores(id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Retrieves all campaign score associations and metrics for this influencer."""
    log = logger.bind(influencer_id=str(id))
    log.info("Fetching influencer campaign scores")

    inf = db.query(models.Influencer).filter(models.Influencer.id == id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    scores = db.query(models.InfluencerScore).filter(models.InfluencerScore.influencer_id == id).all()

    return [
        {
            "score_id": s.id,
            "campaign_id": s.campaign_id,
            "final_score": s.final_score,
            "relevance_score": s.relevance_score,
            "credibility_score": s.credibility_score,
            "engagement_score": s.engagement_score,
            "sentiment_score": s.sentiment_score,
            "brand_safety_score": s.brand_safety_score,
            "confidence_level": s.confidence_level,
            "data_source_count": s.data_source_count,
            "score_version": s.score_version,
            "signal_scores": s.signal_scores or {},
            "risk_category": s.risk_category,
            "detection_category": s.detection_category,
            "positive_reasons": s.positive_reasons or [],
            "negative_reasons": s.negative_reasons or [],
            "source_provenance": s.source_provenance or [],
            "computed_at": s.computed_at,
        }
        for s in scores
    ]


@router.get("/{id}/safety", response_model=list[dict[str, Any]])
def get_influencer_safety_flags(id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Retrieves all brand safety violations/flags raised against this influencer."""
    log = logger.bind(influencer_id=str(id))
    log.info("Fetching influencer brand safety flags")

    inf = db.query(models.Influencer).filter(models.Influencer.id == id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    flags = db.query(models.BrandSafetyFlag).filter(models.BrandSafetyFlag.influencer_id == id).all()

    return [
        {
            "flag_id": f.id,
            "campaign_id": f.campaign_id,
            "source_url": f.source_url,
            "risk_type": f.risk_type,
            "reason": f.reason,
            "severity": f.severity,
            "detection_method": f.detection_method,
            "matched_keyword": f.matched_keyword,
            "context_snippet": f.context_snippet,
            "requires_llm_review": f.requires_llm_review,
            "created_at": f.created_at,
        }
        for f in flags
    ]


@router.get("/{id}/verifications", response_model=list[dict[str, Any]])
def get_influencer_verifications(id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Retrieves all verified credentials (e.g. professional licenses, degrees) for the influencer."""
    log = logger.bind(influencer_id=str(id))
    log.info("Fetching influencer credential verifications")

    inf = db.query(models.Influencer).filter(models.Influencer.id == id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    verifications = db.query(models.CredentialVerification).filter(models.CredentialVerification.influencer_id == id).all()

    return [
        {
            "verification_id": v.id,
            "credential_type": v.credential_type,
            "credential_value": v.credential_value,
            "verified": v.verified,
            "verified_at": v.verified_at,
            "source_url": v.source_url,
            "extracted_claim": v.extracted_claim,
            "verifier": v.verifier,
            "confidence": v.confidence,
            "review_state": v.review_state,
            "created_at": v.created_at,
        }
        for v in verifications
    ]


@router.post("/{id}/deep-analysis", response_model=dict[str, Any])
def start_deep_analysis(
    id: UUID,
    campaign_id: UUID = Query(..., description="Campaign context for the deep analysis run"),
    comment_target: int = Query(default=2000, ge=100, le=10000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Start a deep analysis job for an influencer."""
    inf = db.query(models.Influencer).filter(models.Influencer.id == id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    from uuid import uuid4

    run = models.DeepAnalysisRun(
        id=uuid4(),
        campaign_id=campaign_id,
        influencer_id=id,
        status="queued",
        requested_comment_target=comment_target,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    from backend.pipeline.tasks.deep import deep_analyze

    deep_analyze.delay(str(campaign_id), str(id), str(run.id), comment_target=comment_target)
    return {
        "run_id": str(run.id),
        "status": run.status,
        "campaign_id": str(campaign_id),
        "influencer_id": str(id),
    }


@router.get("/{id}/deep-analysis/{run_id}", response_model=dict[str, Any])
def get_deep_analysis_status(
    id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Poll deep analysis job status."""
    run = (
        db.query(models.DeepAnalysisRun)
        .filter(models.DeepAnalysisRun.id == run_id, models.DeepAnalysisRun.influencer_id == id)
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Deep analysis run not found")
    report = db.query(models.DeepAnalysisReport).filter(models.DeepAnalysisReport.run_id == run.id).first()
    return {
        "run_id": str(run.id),
        "status": run.status,
        "campaign_id": str(run.campaign_id),
        "influencer_id": str(run.influencer_id),
        "collected_comment_count": run.collected_comment_count,
        "provider_coverage": run.provider_coverage or {},
        "failure_reason": run.failure_reason,
        "report": {
            "report_id": str(report.id),
            "overall_grade": report.overall_grade,
            "audience_sentiment": report.audience_sentiment,
            "fake_engagement_risk": report.fake_engagement_risk,
            "recommendation": report.recommendation,
            "confidence": report.confidence,
            "report_payload": report.report_payload,
        }
        if report
        else None,
    }


@router.get("/{id}/reports/{report_id}", response_model=dict[str, Any])
def get_deep_analysis_report(
    id: UUID,
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Fetch a completed deep analysis report."""
    report = (
        db.query(models.DeepAnalysisReport)
        .join(models.DeepAnalysisRun, models.DeepAnalysisRun.id == models.DeepAnalysisReport.run_id)
        .filter(models.DeepAnalysisReport.id == report_id, models.DeepAnalysisRun.influencer_id == id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id": str(report.id),
        "run_id": str(report.run_id),
        "overall_grade": report.overall_grade,
        "audience_sentiment": report.audience_sentiment,
        "fake_engagement_risk": report.fake_engagement_risk,
        "brand_safety_summary": report.brand_safety_summary,
        "recommendation": report.recommendation,
        "confidence": report.confidence,
        "report_payload": report.report_payload,
        "created_at": report.created_at,
    }
