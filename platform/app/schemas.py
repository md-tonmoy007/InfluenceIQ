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


class SignupRequest(BaseModel):
    company_name: str = Field(default="", max_length=255)
    name: str = Field(default="", max_length=255)
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    user_id: str
    company_name: str
    name: str
    email: str


class AuthResponse(BaseModel):
    user: UserResponse


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
    influencer_count: int = 0
    partial_results_available: bool = False
    error: str | None = None


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


class InfluencerListResponse(BaseModel):
    items: list[InfluencerResponse] = Field(default_factory=list)
    total: int = 0
    limit: int
    offset: int
    filters: dict[str, Any] = Field(default_factory=dict)
    sort: dict[str, str] = Field(default_factory=dict)
