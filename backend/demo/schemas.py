from __future__ import annotations

from pydantic import BaseModel, Field


class QueryGenRequest(BaseModel):
    """Brief fields for the query-generation smoke endpoint."""

    product: str = Field(default="", max_length=255)
    niche: str = Field(default="", max_length=255)
    goals: str | None = Field(default=None, max_length=1000)
    target_audience: str | None = Field(default=None, max_length=1000)
    preferred_platforms: list[str] = Field(default_factory=list)


class SearchFilterRequest(BaseModel):
    """Request body for the search + URL filter smoke test."""

    query: str = Field(..., min_length=1, max_length=500)
    product: str = Field(default="", max_length=255)
    niche: str = Field(default="", max_length=255)
    goals: str | None = Field(default=None, max_length=1000)
    target_audience: str | None = Field(default=None, max_length=1000)
    preferred_platforms: list[str] = Field(default_factory=list)


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="URL to fetch, extract, and identify mentions from")
