from __future__ import annotations

from typing import Any

from .fake_comment import extract_comment_features, score_fake_comments


def generic_comment_ratio(comments: list[str]) -> float:
    return round(extract_comment_features(comments)["generic_comment_ratio"], 4)


def repeated_comment_ratio(comments: list[str]) -> float:
    return round(extract_comment_features(comments)["duplicate_comment_ratio"], 4)


def engagement_mismatch(followers: int | float, average_engagement: int | float) -> float:
    followers, engagement = max(0.0, float(followers or 0)), max(0.0, float(average_engagement or 0))
    return round(max(0.0, min(1.0, (0.02 - engagement / followers) / 0.02)), 4) if followers else 0.0


def analyze_fake_engagement(comments: list[str] | None = None, followers: int | float = 0,
                            average_engagement: int | float = 0) -> dict[str, Any]:
    features = extract_comment_features(comments)
    spam_ratio = round(features["duplicate_comment_ratio"], 4)
    generic_ratio = round(features["generic_comment_ratio"], 4)
    mismatch = engagement_mismatch(followers, average_engagement)
    bot_probability = round(max(0.0, min(1.0, spam_ratio * 0.4 + mismatch * 0.4 + generic_ratio * 0.2)), 4)
    reasons = score_fake_comments(features)["reasons"]
    if mismatch >= 0.5: reasons.append("Engagement is unusually low relative to follower count.")
    if not reasons: reasons.append("No strong fake-engagement signals detected.")
    return {"spam_ratio": spam_ratio, "engagement_mismatch": mismatch, "generic_comment_ratio": generic_ratio,
            "bot_probability": bot_probability, "engagement_quality": round((1 - bot_probability) * 100, 2),
            "reasons": reasons}
