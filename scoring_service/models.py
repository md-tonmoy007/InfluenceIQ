from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class RiskComponent(TypedDict):
    score: float | None
    weight: float
    contribution: float
    available: bool


class RiskScore(TypedDict):
    score: float
    risk_category: str
    components: dict[str, RiskComponent]
    renormalized: bool
    model_version: str
    computed_at: str


class InfluencerOutput(TypedDict):
    influencer_id: str
    canonical_name: str
    platforms: dict[str, str]
    profile_urls: list[str]
    credentials: list[str]
    professional_titles: list[str]
    mentions: list[dict[str, Any]]
    sub_scores: dict[str, float]
    signal_scores: dict[str, float | None]
    risk_score: RiskScore
    grade: str
    confidence: str
    data_source_count: int
    positive_reasons: list[str]
    negative_reasons: list[str]
    source_urls: list[str]
    requires_human_review: bool
    explanation: NotRequired[str]
