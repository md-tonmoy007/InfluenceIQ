from __future__ import annotations

from typing import Any


def confidence_for_source_count(data_source_count: int) -> str:
    if data_source_count < 3: return "Low"
    if data_source_count <= 5: return "Medium"
    return "High"


def calculate_credibility(*, verified: bool = False, professional_titles: list[str] | None = None,
                          authority_mentions: int = 0, credentials: list[str] | None = None,
                          sentiment_score: float = 50.0, engagement_quality: float = 50.0,
                          bot_probability: float = 0.0, brand_safety_risks: dict[str, bool] | None = None,
                          data_source_count: int = 0, complete_profile: bool = False,
                          fake_comment_risk_score: float = 0.0, fake_follower_risk_score: float = 0.0,
                          bot_behavior_risk_score: float = 0.0, coordinated_engagement_risk_score: float = 0.0,
                          spam_indicators: bool = False, brand_safety_score: float | None = None) -> dict[str, Any]:
    score, positive, negative = 50.0, [], []
    def add(points: float, reason: str) -> None:
        nonlocal score; score += points; (positive if points > 0 else negative).append(reason)
    if verified: add(10, "Verified account")
    if professional_titles: add(15, "Professional title found")
    if authority_mentions > 0: add(20, "Authority mention found")
    if credentials: add(20, "Educational credential found")
    if sentiment_score >= 61: add(15, "Positive sentiment evidence")
    if engagement_quality >= 70: add(10, "High engagement quality")
    if data_source_count >= 3: add(10, "Multiple independent sources")
    if complete_profile: add(10, "Complete profile")
    if spam_indicators or bot_probability >= 0.5: add(-20, "Spam indicators detected")
    safety_risky = (brand_safety_score is not None and brand_safety_score < 65) or any((brand_safety_risks or {}).values())
    if safety_risky: add(-25, "Brand-safety risk detected")
    if fake_comment_risk_score >= 41: add(-20, "High fake comment risk")
    if fake_follower_risk_score >= 41: add(-20, "High fake follower risk")
    if bot_behavior_risk_score >= 41: add(-15, "Bot behavior risk")
    if coordinated_engagement_risk_score >= 41: add(-15, "Coordinated engagement risk")
    if data_source_count < 3: add(-10, "Low source count")
    raw = score
    score = max(0.0, min(100.0, score))
    capped = data_source_count < 3 and score > 70
    if capped:
        score = 70.0
        negative.append("Score capped at 70 because fewer than 3 sources contributed")
    return {"credibility_score": round(score, 2), "raw_score": round(raw, 2), "confidence": confidence_for_source_count(data_source_count),
            "confidence_capped": capped, "positive_reasons": positive, "negative_reasons": negative,
            "reasons": [*positive, *negative] or ["Baseline credibility only; more evidence is required."]}
