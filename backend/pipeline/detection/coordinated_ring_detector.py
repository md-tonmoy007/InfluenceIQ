"""Pipeline 7 - Coordinated Engagement Detection.

Wraps :mod:`backend.pipeline.analysis.coordinated_engagement`. The
detection result is enriched with a categorical label (LOW / MEDIUM /
HIGH / SPAM_RING) and a ``is_spam_ring`` boolean that the role-5
classifier consumes.

    coordinated_engagement_risk_score = 100 * clamp(
        0.30 * repeated_commenter_cluster_score
      + 0.25 * duplicate_text_cluster_score
      + 0.20 * synchronized_activity_score
      + 0.15 * shared_hashtag_cluster_score
      + 0.10 * suspicious_account_overlap_score
    )
"""

from __future__ import annotations

from typing import Any

from backend.pipeline.analysis.coordinated_engagement import score_coordinated_engagement


def detect_coordinated_engagement(features: dict[str, Any]) -> dict[str, Any]:
    """Run coordinated-engagement detection on the supplied feature dict."""
    result = score_coordinated_engagement(features)
    score_value = float(result["coordinated_engagement_risk_score"])
    return {
        "detector": "coordinated_engagement",
        "score": score_value,
        "category": result["category"],
        "is_spam_ring": score_value > 80,
        "reasons": list(result.get("reasons", [])),
        "evidence": result.get("evidence", {}),
    }
