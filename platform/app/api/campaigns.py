from __future__ import annotations

from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import models
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.schemas.influencer import InfluencerResponse, SubScores
from app.services.pipeline_state import (
    initialize_pipeline_state,
    get_pipeline_state,
)
from app.tasks.search import generate_queries

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=dict[str, Any])
def create_campaign(
    campaign_data: CampaignCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Creates a campaign in the DB, sets up Redis state tracking, and dispatches the Celery pipeline."""
    # Create DB campaign entry
    db_campaign = models.Campaign(
        product=campaign_data.product,
        niche=campaign_data.industry,
        goals=campaign_data.goals,
        target_audience=campaign_data.target_audience,
        preferred_platforms=campaign_data.preferred_platforms,
        budget_range=campaign_data.budget_range,
        weights=campaign_data.weights.model_dump() if campaign_data.weights else None,
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)

    campaign_id_str = str(db_campaign.id)

    # Initialize tracking state in Redis
    initialize_pipeline_state(campaign_id_str)

    # Dispatch Celery task pipeline asynchronously (starting with query generation)
    generate_queries.delay(campaign_id_str)

    return {
        "campaign_id": db_campaign.id,
        "status": "started",
        "pipeline_state": get_pipeline_state(campaign_id_str),
    }


@router.get("/{id}", response_model=dict[str, Any])
def get_campaign(id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieves campaign metadata along with the current pipeline execution state."""
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign_id_str = str(id)
    # Fetch execution state from Redis
    state = get_pipeline_state(campaign_id_str) or {
        "campaign_id": campaign_id_str,
        "phase": "finished",
        "message": "Redis state expired, read database for outcomes."
    }

    return {
        "campaign": CampaignResponse.model_validate(db_campaign),
        "pipeline_state": state,
    }


@router.get("/{id}/state", response_model=dict[str, Any])
def get_campaign_state(id: UUID) -> dict[str, Any]:
    """Fast-path fallback to retrieve only execution progress from Redis state cache."""
    campaign_id_str = str(id)
    state = get_pipeline_state(campaign_id_str)
    if not state:
        raise HTTPException(
            status_code=404, detail="State cache not found or expired for campaign"
        )
    return state


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
    """Retrieves scored and ranked influencers discovered for a specific campaign.
    Supports filtering, pagination, and sorting by final score.
    """
    # Ensure campaign exists
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Build query joining influencer_scores and influencers
    query = (
        db.query(models.InfluencerScore, models.Influencer)
        .join(models.Influencer, models.InfluencerScore.influencer_id == models.Influencer.id)
        .filter(models.InfluencerScore.campaign_id == id)
    )

    # Apply platform filters
    if platform:
        # Check platforms JSONB field for presence of the specific platform key
        query = query.filter(models.Influencer.platforms.has_key(platform.lower()))

    # Apply niche filter
    if niche:
        # Check if niche is mentioned in the canonical name or platforms or credentials
        query = query.filter(models.Influencer.canonical_name.ilike(f"%{niche}%"))

    # Apply grade filter
    if grade:
        # Helper to map grades back to score boundaries
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

    # Order by final score DESC (highest trust first)
    query = query.order_by(models.InfluencerScore.final_score.desc())

    # Paginate
    results = query.limit(limit).offset(offset).all()

    response_list = []
    for score, inf in results:
        # Fetch sources for this influencer and campaign to satisfy provenance requirements
        sources_list = (
            db.query(models.CrawlSource)
            .filter(
                models.CrawlSource.campaign_id == id,
                models.CrawlSource.influencer_id == inf.id
            )
            .all()
        )
        
        from app.schemas.influencer import CrawlSourceResponse
        sources_response = [
            CrawlSourceResponse(
                url=src.url,
                title=src.title,
                relevance_score=src.relevance_score,
                status=src.status
            )
            for src in sources_list
        ]

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
                sources=sources_response,
            )
        )

    return response_list

