from __future__ import annotations

from typing import Any


def normalize_score(value: Any, default: float = 0.0) -> float:
    """Coerce a raw score into the inclusive 0-100 range."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default

    if score < 0:
        return 0.0
    if score > 100:
        return 100.0
    return round(score, 2)


def normalize_sub_scores(sub_scores: dict[str, Any], defaults: dict[str, float]) -> dict[str, float]:
    return {
        name: normalize_score(sub_scores.get(name, default), default)
        for name, default in defaults.items()
    }
