from __future__ import annotations

from typing import Any

from app.config import settings
from app.scoring.normalize import normalize_sub_scores

DEFAULT_SUB_SCORE_VALUES = {
    "relevance": 50.0,
    "credibility": 50.0,
    "engagement": 50.0,
    "sentiment": 50.0,
    "brand_safety": 50.0,
}

DEFAULT_WEIGHTS = {
    "relevance": 0.30,
    "credibility": 0.25,
    "engagement": 0.20,
    "sentiment": 0.10,
    "brand_safety": 0.15,
}


def grade_for_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def calculate_final_score(
    sub_scores: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    normalized = normalize_sub_scores(sub_scores, DEFAULT_SUB_SCORE_VALUES)
    active_weights = weights or DEFAULT_WEIGHTS
    total_weight = sum(active_weights.values()) or 1.0
    weighted_score = sum(normalized[name] * active_weights.get(name, 0.0) for name in normalized)
    return round(weighted_score / total_weight, 2), normalized


def confidence_for_sources(data_source_count: int, final_score: float) -> tuple[str, float]:
    capped_score = final_score
    if data_source_count < settings.CONFIDENCE_CAP_THRESHOLD:
        capped_score = min(final_score, float(settings.CONFIDENCE_CAP_VALUE))

    if data_source_count >= 6:
        confidence = "High"
    elif data_source_count >= settings.CONFIDENCE_CAP_THRESHOLD:
        confidence = "Medium"
    else:
        confidence = "Low"

    return confidence, round(capped_score, 2)
