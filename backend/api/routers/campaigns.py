from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.schemas.campaign import CampaignCreate, CampaignResponse
from backend.api.schemas.influencer import CrawlSourceResponse, InfluencerResponse, SubScores
from backend.core.cache.pipeline_state import (
    get_pipeline_state,
    initialize_pipeline_state,
)
from backend.core.database import models
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=dict[str, Any])
def create_campaign(
    campaign_data: CampaignCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Create a campaign, initialize transient state, and dispatch the pipeline."""
    db_campaign = models.Campaign(
        product=campaign_data.product,
        niche=campaign_data.industry,
        goals=campaign_data.goals,
        target_audience=campaign_data.target_audience,
        preferred_platforms=campaign_data.preferred_platforms,
        budget_range=campaign_data.budget_range,
        weights=campaign_data.weights.model_dump() if campaign_data.weights else None,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)

    campaign_id_str = str(db_campaign.id)
    initialize_pipeline_state(campaign_id_str)

    try:
        from backend.pipeline.tasks import start_pipeline

        start_pipeline(campaign_id_str)
    except Exception as exc:
        db_campaign.status = "failed"
        db_campaign.failed_at = datetime.now(UTC)
        db_campaign.failure_reason = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {exc}") from exc

    return {
        "campaign_id": db_campaign.id,
        "status": db_campaign.status,
        "pipeline_state": get_campaign_state_payload(db_campaign, campaign_id_str),
    }


@router.get("/{id}", response_model=dict[str, Any])
def get_campaign(id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve campaign metadata along with current transient pipeline state."""
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign_id_str = str(id)
    return {
        "campaign": CampaignResponse.model_validate(db_campaign),
        "pipeline_state": get_campaign_state_payload(db_campaign, campaign_id_str),
    }


@router.get("/{id}/state", response_model=dict[str, Any])
def get_campaign_state(id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve execution progress, falling back to the durable campaign lifecycle state."""
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return get_campaign_state_payload(db_campaign, str(id))


@router.get("/{id}/influencers", response_model=list[InfluencerResponse])
def get_campaign_influencers(
    id: UUID,
    platform: str | None = Query(default=None, description="Filter by platform handle availability"),
    grade: str | None = Query(default=None, description="Filter by trust grade, e.g. 'A+', 'A'"),
    niche: str | None = Query(default=None, description="Filter by core niche"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[InfluencerResponse]:
    """Retrieve ranked influencers for a campaign with durable provenance details."""
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = (
        db.query(models.InfluencerScore, models.Influencer)
        .join(models.Influencer, models.InfluencerScore.influencer_id == models.Influencer.id)
        .filter(models.InfluencerScore.campaign_id == id)
    )

    if platform:
        query = query.filter(models.Influencer.platforms.has_key(platform.lower()))
    if niche:
        query = query.filter(models.Influencer.canonical_name.ilike(f"%{niche}%"))
    if grade:
        grade_bounds = {
            "A+": (90.0, 100.0),
            "A": (80.0, 89.99),
            "B": (70.0, 79.99),
            "C": (60.0, 69.99),
            "D": (0.0, 59.99),
        }
        bounds = grade_bounds.get(grade.upper())
        if bounds:
            query = query.filter(
                models.InfluencerScore.final_score >= bounds[0],
                models.InfluencerScore.final_score <= bounds[1],
            )

    results = query.order_by(models.InfluencerScore.final_score.desc()).limit(limit).offset(offset).all()

    response_list = []
    for score, inf in results:
        sources_response = _campaign_influencer_sources(db, id, inf.id)
        response_list.append(
            InfluencerResponse(
                influencer_id=inf.id,
                canonical_name=inf.canonical_name,
                platforms=inf.platforms or {},
                credentials=inf.credentials or [],
                mentions=inf.mentions or [],
                final_score=score.final_score,
                sub_scores=SubScores(
                    relevance=score.relevance_score,
                    credibility=score.credibility_score,
                    engagement=score.engagement_score,
                    sentiment=score.sentiment_score,
                    brand_safety=score.brand_safety_score,
                ),
                confidence=score.confidence_level,
                data_source_count=score.data_source_count,
                score_version=score.score_version,
                computed_at=score.computed_at,
                signal_scores=score.signal_scores or {},
                risk_category=score.risk_category,
                detection_category=score.detection_category,
                positive_reasons=score.positive_reasons or [],
                negative_reasons=score.negative_reasons or [],
                sources=sources_response,
            )
        )

    return response_list


def get_campaign_state_payload(campaign: models.Campaign, campaign_id_str: str) -> dict[str, Any]:
    state = get_pipeline_state(campaign_id_str)
    if state:
        state.setdefault("status", campaign.status)
        state.setdefault("started_at", campaign.started_at.isoformat() if campaign.started_at else None)
        return state
    return {
        "campaign_id": campaign_id_str,
        "status": campaign.status,
        "phase": campaign.status,
        "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
        "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
        "failed_at": campaign.failed_at.isoformat() if campaign.failed_at else None,
        "failure_reason": campaign.failure_reason,
        "message": "Redis state unavailable; returning durable campaign lifecycle state.",
    }


def _campaign_influencer_sources(db: Session, campaign_id: UUID, influencer_id: UUID) -> list[CrawlSourceResponse]:
    links = (
        db.query(models.CrawlSourceInfluencer, models.CrawlSource)
        .join(models.CrawlSource, models.CrawlSource.id == models.CrawlSourceInfluencer.crawl_source_id)
        .filter(
            models.CrawlSource.campaign_id == campaign_id,
            models.CrawlSourceInfluencer.influencer_id == influencer_id,
        )
        .all()
    )
    if links:
        return [
            CrawlSourceResponse(
                url=source.url,
                title=source.title,
                relevance_score=source.relevance_score,
                status=source.status,
                mention_id=link.mention_id,
                mention=link.mention,
            )
            for link, source in links
        ]

    legacy_sources = (
        db.query(models.CrawlSource)
        .filter(
            models.CrawlSource.campaign_id == campaign_id,
            models.CrawlSource.influencer_id == influencer_id,
        )
        .all()
    )
    return [
        CrawlSourceResponse(
            url=src.url,
            title=src.title,
            relevance_score=src.relevance_score,
            status=src.status,
        )
        for src in legacy_sources
    ]
