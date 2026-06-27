"""Pipeline versioning helpers.

The role-4 spec uses ``Role4-InfluenceScore-v1`` (heuristics) and
``Role4-InfluenceScore-v2`` (when any v2 ML adapter fires).
"""

from __future__ import annotations

from datetime import UTC, datetime

MODEL_VERSION: str = "Role4-InfluenceScore-v1"
MODEL_VERSION_V2: str = "Role4-InfluenceScore-v2"


def computed_at() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def model_version_for(
    *,
    semantic_v2: bool,
    behavioral_v2: bool,
    graph_v2: bool,
    bot_rings_v2: bool,
) -> str:
    """Return v2 when any v2 adapter fired, else v1.

    The LLM explainer is intentionally excluded — it does not change
    the underlying scoring model version.
    """
    if any((semantic_v2, behavioral_v2, graph_v2, bot_rings_v2)):
        return MODEL_VERSION_V2
    return MODEL_VERSION


__all__ = [
    "MODEL_VERSION",
    "MODEL_VERSION_V2",
    "computed_at",
    "model_version_for",
]
