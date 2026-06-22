from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    """Payload submitted by the "Your brand" -> "Goals" -> "Platforms" wizard."""
    brand_name: str = Field(..., min_length=1, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    company_size: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=100)
    goals: list[str] | None = Field(default=None, description="e.g. ['awareness', 'sales']")
    platforms: list[str] | None = Field(default=None, description="e.g. ['instagram', 'tiktok']")
    monthly_budget: int | None = Field(default=None, ge=0)


class OnboardingResponse(BaseModel):
    id: UUID
    user_id: UUID
    brand_name: str
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    goals: list[str] | None = None
    platforms: list[str] | None = None
    monthly_budget: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
