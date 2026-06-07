from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CampaignBriefPayload(BaseModel):
    brand: str = ""
    product: str = ""
    category: str = ""
    goal: str = ""
    ages: list[str] = Field(default_factory=list)
    gender: str = ""
    locations: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    tier: str = ""
    budget: str = ""


class CampaignCreatedResponse(BaseModel):
    campaign_id: str
    status: str


class CampaignResponse(BaseModel):
    campaign_id: str
    brand: str
    product: str
    category: str
    goal: str
    status: str
    created_at: datetime
    payload: dict[str, Any]
    pipeline_state: dict[str, Any]


class InfluencerResponse(BaseModel):
    id: str
    name: str
    handle: str
    platform: str
    followers: int
    engagementRate: float
    matchScore: float
    trustGrade: str
    brandSafetyFlags: list[str]
    citations: list[str]
    rate: str
    sub_scores: dict[str, float] = Field(default_factory=dict)
    score_payload: dict[str, Any] = Field(default_factory=dict)
    source_payload: dict[str, Any] = Field(default_factory=dict)
