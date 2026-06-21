from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CampaignWeights(BaseModel):
    """Custom weight distribution for final scoring. Sub-scores must sum to 1.0."""
    relevance: float = Field(default=0.30, ge=0.0, le=1.0)
    credibility: float = Field(default=0.30, ge=0.0, le=1.0)
    engagement: float = Field(default=0.20, ge=0.0, le=1.0)
    sentiment: float = Field(default=0.10, ge=0.0, le=1.0)
    brand_safety: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_weights_sum(self) -> CampaignWeights:
        weights_sum = (
            self.relevance
            + self.credibility
            + self.engagement
            + self.sentiment
            + self.brand_safety
        )
        if not (0.99 <= weights_sum <= 1.01):
            raise ValueError(f"Custom weights must sum to 1.0 (currently {weights_sum})")
        return self


class CampaignCreate(BaseModel):
    """Payload for submitting new brand influencer search campaigns."""
    product: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(..., min_length=1, max_length=255, description="Campaign niche/vertical")
    goals: str | None = Field(default=None, max_length=1000)
    target_audience: str | None = Field(default=None, max_length=1000)
    preferred_platforms: list[str] | None = Field(default=None, description="e.g. ['instagram', 'youtube']")
    budget_range: str | None = Field(default=None, max_length=100)
    weights: CampaignWeights | None = Field(default=None)


class CampaignResponse(BaseModel):
    """Response returned for queries requesting campaign info."""
    id: UUID
    brand_id: UUID | None
    product: str
    niche: str
    goals: str | None
    target_audience: str | None
    preferred_platforms: list[str] | None
    budget_range: str | None
    weights: dict[str, float] | None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
