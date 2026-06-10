from __future__ import annotations

import re
from typing import Any

from scoring_service.model_classifiers import classify_with_model


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _signal(value: bool) -> float:
    return 1.0 if value else 0.0


def score_fake_followers(features: dict[str, Any]) -> dict[str, Any]:
    followers = max(0.0, float(features.get("follower_count", features.get("followers", 0)) or 0))
    following = max(0.0, float(features.get("following_count", features.get("following", 0)) or 0))
    age = max(0.0, float(features.get("account_age_days", 0) or 0))
    posts = max(0.0, float(features.get("post_count", 0) or 0))
    if features.get("engagement_rate") is not None:
        actual = max(0.0, float(features.get("engagement_rate") or 0))
    elif followers and features.get("average_engagement", features.get("avg_engagement")) is not None:
        actual = max(0.0, float(features.get("average_engagement", features.get("avg_engagement")) or 0)) / followers
    else:
        actual = expected = max(0.0001, float(features.get("expected_engagement_rate", 0.02) or 0.02))
    if actual > 1:
        actual /= 100
    expected = max(0.0001, float(features.get("expected_engagement_rate", 0.02) or 0.02))
    handle = str(features.get("handle", ""))
    ratio = followers / max(following, 1.0)
    suspicious_handle = bool(features.get("suspicious_handle_pattern", re.search(r"(?:\d{5,}|[_\-.]{3,})", handle)))
    signals = {
        "no_profile_picture_signal": _signal(features.get("profile_picture_present") is False),
        "no_bio_signal": _signal(features.get("bio_present") is False),
        "new_account_high_followers_signal": _signal("account_age_days" in features and age < 90 and followers >= 10_000),
        "abnormal_ratio_signal": _signal(("following_count" in features or "following" in features) and (ratio > 100 or ratio < 0.02) and followers > 100),
        "suspicious_username_signal": _signal(bool(handle) and suspicious_handle),
    }
    profile_anomaly = sum(signals.values()) / len(signals)
    mismatch = _clamp(abs(expected - actual) / expected)
    abnormal_ratio = _clamp(features.get("abnormal_follower_ratio_score", signals["abnormal_ratio_signal"]))
    growth = _clamp(features.get("follower_growth_anomaly_score", 0))
    low_activity_default = _signal(("post_count" in features) and followers >= 10_000 and posts < 20)
    low_activity = _clamp(features.get("low_activity_high_followers_score", low_activity_default))
    heuristic = 100 * _clamp(0.25 * profile_anomaly + 0.25 * mismatch + 0.20 * abnormal_ratio + 0.15 * growth + 0.15 * low_activity)
    model_result = None
    model_probability = features.get("model_fake_follower_probability", features.get("model_suspicious_follower_probability"))
    if model_probability is None:
        model_result = classify_with_model("fake_followers", {"features": {**features, **signals, "engagement_mismatch_score": mismatch}})
        if model_result is not None:
            model_probability = model_result.risk_probability
    score = 0.60 * _clamp(model_probability) * 100 + 0.40 * heuristic if model_probability is not None else heuristic
    reasons, evidence = [], {**signals, "engagement_mismatch_score": mismatch, "follower_to_following_ratio": round(ratio, 4)}
    if mismatch >= 0.5: reasons.append("Follower count is high but engagement is low")
    if signals["no_profile_picture_signal"] or signals["no_bio_signal"]: reasons.append("Profile completeness is weak")
    if abnormal_ratio >= 0.5: reasons.append("Follower/following ratio is abnormal")
    if growth >= 0.5: reasons.append("Follower growth pattern looks suspicious")
    if mismatch >= 0.5: reasons.append("Engagement does not match audience size")
    model_evidence = model_result.to_evidence() if model_result is not None else {}
    if model_result is not None:
        reasons.extend(model_result.reasons)
        evidence.update(model_evidence)
    return {"fake_follower_risk_score": round(score, 2), "profile_anomaly_score": round(profile_anomaly, 4),
            "heuristic_fake_follower_risk_score": round(heuristic, 2),
            "model_fake_follower_probability": round(_clamp(model_probability), 4) if model_probability is not None else None,
            "model_provider": model_evidence.get("model_provider"),
            "model_name": model_evidence.get("model_name"),
            "engagement_mismatch_score": round(mismatch, 4), "reasons": list(dict.fromkeys(reasons)), "evidence": evidence}
