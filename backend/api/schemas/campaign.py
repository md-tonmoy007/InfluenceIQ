from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class CampaignWeights(BaseModel):
    """Custom weight distribution for final scoring. Sub-scores must sum to 1.0."""
    relevance: float = Field(default=0.30, ge=0.0, le=1.0)
    credibility: float = Field(default=0.30, ge=0.0, le=1.0)
    engagement: float = Field(default=0.20, ge=0.0, le=1.0)
    sentiment: float = Field(default=0.10, ge=0.0, le=1.0)
    brand_safety: float = Field(default=0.10, ge=0.0, le=1.0)
    source_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_weights_sum(self) -> CampaignWeights:
        weights_sum = (
            self.relevance
            + self.credibility
            + self.engagement
            + self.sentiment
            + self.brand_safety
            + self.source_confidence
        )
        if not (0.99 <= weights_sum <= 1.01):
            raise ValueError(f"Custom weights must sum to 1.0 (currently {weights_sum})")
        return self


class BriefSnapshot(BaseModel):
    """Typed capture of the brief-form fields persisted on the campaign.

    Lets the workspace shell render the original brief inputs
    (audience tiers, locations, interests, etc.) on the shortlist /
    briefs pages without re-deriving them from the ``goals`` /
    ``target_audience`` prose blob.
    """
    brand_name: str | None = Field(default=None, max_length=255)
    campaign_name: str | None = Field(default=None, max_length=255)
    goals: list[str] = Field(default_factory=list)
    goal: str | None = Field(default=None, max_length=255)
    ages: list[str] = Field(default_factory=list)
    gender: str | None = Field(default=None, max_length=32)
    language: str | None = Field(default=None, max_length=64)
    locations: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    tier: str | None = Field(default=None, max_length=64)
    budget_text: str | None = Field(default=None, max_length=255)
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    notes: str | None = Field(default=None)


class CampaignCreate(BaseModel):
    """Payload for submitting new brand influencer search campaigns."""
    search_query: str = Field(
        ..., min_length=1, description="Raw text describing the campaign/product, used to drive influencer search."
    )
    preferred_platforms: list[str] | None = Field(default=None, description="e.g. ['instagram', 'youtube']")
    budget_range: str | None = Field(default=None, max_length=100)
    weights: CampaignWeights | None = Field(default=None)

    entry_point: str | None = Field(
        default="brief_form",
        description="Where the campaign was created: 'brief_form', 'discover_search', 'topbar_search'.",
    )
    campaign_name: str | None = Field(
        default=None, max_length=255, description="Display label for the workspace shell."
    )
    brief_snapshot: BriefSnapshot | None = Field(
        default=None, description="Typed brief form fields, persisted for UI display."
    )
    start_pipeline: bool = Field(
        default=True,
        description="When false, create a draft campaign without starting the matching pipeline.",
    )

    @field_validator("entry_point")
    @classmethod
    def _validate_entry_point(cls, value: str | None) -> str | None:
        """Restrict entry_point to the small enum the workspace shell knows about."""
        if value is None:
            return None
        allowed = {"brief_form", "discover_search", "topbar_search"}
        if value not in allowed:
            raise ValueError(
                f"entry_point must be one of {sorted(allowed)}; got {value!r}."
            )
        return value


class CampaignUpdate(BaseModel):
    """Payload for updating a draft campaign before submission."""
    search_query: str | None = Field(default=None, min_length=1)
    preferred_platforms: list[str] | None = Field(default=None)
    budget_range: str | None = Field(default=None, max_length=100)
    campaign_name: str | None = Field(default=None, max_length=255)
    brief_snapshot: BriefSnapshot | None = Field(default=None)


class CampaignContractCreate(BaseModel):
    """Mark or update outreach status for a creator on a campaign."""
    influencer_id: UUID
    status: str = Field(default="contracted", pattern="^(contracted|pending|declined)$")
    notes: str | None = Field(default=None, max_length=2000)


class CampaignResponse(BaseModel):
    """Response returned for queries requesting campaign info."""
    id: UUID
    brand_id: UUID | None = None
    org_id: UUID | None = None
    created_by: UUID | None = None
    product: str | None = None
    niche: str | None = None
    goals: str | None = None
    target_audience: str | None = None
    preferred_platforms: list[str] | None = None
    budget_range: str | None = None
    weights: dict[str, float] | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    campaign_name: str | None = None
    entry_point: str | None = None
    search_query: str | None = None
    brief_snapshot: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    influencer_count: int | None = Field(
        default=None,
        description="Best-effort count of influencers scored for this campaign; computed by the listing endpoint.",
    )
    top_match_score: float | None = Field(
        default=None,
        description="Highest final_score across the campaign's influencer scores; computed by the listing endpoint.",
    )
    last_activity_at: datetime | None = Field(
        default=None,
        description="Most recent activity timestamp (updated_at or pipeline event) for the campaign.",
    )
    shortlisted_count: int | None = Field(
        default=None,
        description="Count of saved-list items sourced from this campaign for the current user.",
    )
    contracted_count: int | None = Field(
        default=None,
        description="Count of contracted creators on this campaign.",
    )

    class Config:
        from_attributes = True
