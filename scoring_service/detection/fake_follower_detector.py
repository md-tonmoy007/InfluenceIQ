"""Pipeline 5 - Fake Follower Detection.

The underlying formula is documented in ``Role-5-Scoring.md`` and
implemented in :mod:`scoring_service.analysis.fake_follower`. This module
simply wraps the scorer and produces a detection-shaped payload:

    fake_follower_risk_score = 100 * clamp(
        0.25 * profile_anomaly_score
      + 0.25 * engagement_mismatch_score
      + 0.20 * abnormal_follower_ratio_score
      + 0.15 * follower_growth_anomaly_score
      + 0.15 * low_activity_high_followers_score
    )
"""

from __future__ import annotations

from typing import Any

from scoring_service.analysis.fake_follower import score_fake_followers


def detect_fake_followers(features: dict[str, Any]) -> dict[str, Any]:
    """Run fake-follower detection on the supplied feature dictionary."""
    result = score_fake_followers(features)
    return {
        "detector": "fake_follower",
        "score": result["fake_follower_risk_score"],
        "profile_anomaly_score": result["profile_anomaly_score"],
        "engagement_mismatch_score": result["engagement_mismatch_score"],
        "is_fake_follower": result["fake_follower_risk_score"] > 70,
        "reasons": list(result.get("reasons", [])),
        "evidence": result.get("evidence", {}),
    }
