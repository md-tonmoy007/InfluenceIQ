from __future__ import annotations

from pydantic import BaseModel, Field


class QueryGenRequest(BaseModel):
    """Brief fields for the query-generation smoke endpoint."""

    description: str = Field(default="", max_length=1000)
    locations: list[str] = Field(default_factory=list)
    preferred_platforms: list[str] = Field(default_factory=list)


class SearchFilterRequest(BaseModel):
    """Request body for the search + URL filter smoke test."""

    query: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=1000)
    locations: list[str] = Field(default_factory=list)
    preferred_platforms: list[str] = Field(default_factory=list)


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="URL to fetch, extract, and identify mentions from")
