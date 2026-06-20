"""Pipeline 6 - Bot Behavior Detection.

Wraps :mod:`backend.pipeline.analysis.bot_behavior` and surfaces the
detection result with the spec's risk-band flag for ``BOT_LIKE``.

    bot_behavior_risk_score = 100 * clamp(
        0.25 * posting_interval_uniformity
      + 0.20 * comment_interval_uniformity
      + 0.20 * same_text_reuse_ratio
      + 0.15 * engagement_burst_score
      + 0.10 * night_activity_ratio
      + 0.10 * activity_velocity_score
    )
"""

from __future__ import annotations

from typing import Any

from backend.pipeline.analysis.bot_behavior import score_bot_behavior


def detect_bot_behavior(features: dict[str, Any]) -> dict[str, Any]:
    """Run bot-behavior detection on the supplied feature dictionary."""
    result = score_bot_behavior(features)
    return {
        "detector": "bot_behavior",
        "score": result["bot_behavior_risk_score"],
        "is_bot_like": result["bot_behavior_risk_score"] > 70,
        "reasons": list(result.get("reasons", [])),
        "evidence": result.get("evidence", {}),
    }
