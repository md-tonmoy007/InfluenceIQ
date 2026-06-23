from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubScores(BaseModel):
    """Pydantic model representing sub-scores normalized on [0, 100]."""
    relevance: float = Field(..., ge=0.0, le=100.0)
    credibility: float = Field(..., ge=0.0, le=100.0)
    engagement: float = Field(..., ge=0.0, le=100.0)
    sentiment: float = Field(..., ge=0.0, le=100.0)
    brand_safety: float = Field(..., ge=0.0, le=100.0)


class InfluencerMention(BaseModel):
    """Context details regarding a crawl mention of an influencer."""
    name: str
    source_url: str
    context: str | None = None


class CrawlSourceResponse(BaseModel):
    """Pydantic model representing crawl source provenance details."""
    url: str
    title: str | None = None
    relevance_score: float | None = None
    status: str
    mention_id: str | None = None
    mention: dict | None = None

    class Config:
        from_attributes = True


class InfluencerResponse(BaseModel):
    """Detailed profile data model returned to frontend for a scored influencer."""
    influencer_id: UUID
    canonical_name: str
    platforms: dict[str, str] = Field(default_factory=dict)
    credentials: list[str] | None = Field(default_factory=list)
    mentions: list[dict] | None = Field(default_factory=list)

    final_score: float | None = None
    sub_scores: SubScores | None = None
    confidence: str | None = None
    data_source_count: int = 0
    score_version: str | None = None
    computed_at: datetime | None = None
    signal_scores: dict | None = None
    risk_category: str | None = None
    detection_category: str | None = None
    positive_reasons: list[str] | None = Field(default_factory=list)
    negative_reasons: list[str] | None = Field(default_factory=list)

    sources: list[CrawlSourceResponse] | None = Field(default_factory=list)

    # Best-effort per-platform metrics. Populated by the pipeline when
    # available; left as None when the extraction didn't capture them.
    primary_platform: str | None = None
    primary_handle: str | None = None
    follower_count: int | None = None
    engagement_rate: float | None = None
    avg_views: int | None = None
    primary_category: str | None = None
    primary_location: str | None = None

    class Config:
        from_attributes = True
