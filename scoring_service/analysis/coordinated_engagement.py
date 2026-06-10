from __future__ import annotations

from typing import Any


def _clamp(value: Any) -> float:
    try: return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError): return 0.0


def coordinated_category(score: float) -> str:
    if score <= 20: return "LOW"
    if score <= 45: return "MEDIUM"
    if score <= 70: return "HIGH"
    return "SPAM_RING"


def score_coordinated_engagement(features: dict[str, Any]) -> dict[str, Any]:
    values = {name: _clamp(features.get(name, 0)) for name in (
        "repeated_commenter_cluster_score", "duplicate_text_cluster_score", "synchronized_activity_score",
        "shared_hashtag_cluster_score", "suspicious_account_overlap_score")}
    score = 100 * _clamp(0.30 * values["repeated_commenter_cluster_score"] + 0.25 * values["duplicate_text_cluster_score"]
        + 0.20 * values["synchronized_activity_score"] + 0.15 * values["shared_hashtag_cluster_score"]
        + 0.10 * values["suspicious_account_overlap_score"])
    reasons = []
    if values["repeated_commenter_cluster_score"] >= 0.5: reasons.append("Same accounts repeatedly engage with the same influencer")
    if values["duplicate_text_cluster_score"] >= 0.4: reasons.append("Duplicate comment clusters detected")
    if values["synchronized_activity_score"] >= 0.5: reasons.append("Engagement appears synchronized")
    if score > 45: reasons.append("Possible coordinated engagement ring")
    return {"coordinated_engagement_risk_score": round(score, 2), "category": coordinated_category(score),
            "reasons": reasons, "evidence": {key: value for key, value in values.items() if value > 0}}
