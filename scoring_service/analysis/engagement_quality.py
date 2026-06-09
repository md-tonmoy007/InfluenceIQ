"""Pipeline 11 - Engagement Quality Score.

Engagement quality must **decrease** when fake signals increase:

    engagement_quality_score = clamp(100 - overall_fake_risk_score
                                    + authentic_engagement_bonus, 0, 100)

The authentic bonus is capped at 10 points and is derived from the
supplied diversity, context-relevance, stability, ratio, and
source-diversity evidence. The bonus intentionally accepts the same
feature names the rest of the role-5 pipeline uses so callers do not
have to remap data.
"""

from __future__ import annotations

from typing import Any

from scoring_service.scoring.normalize import clamp, ratio
from scoring_service.scoring.risk_components import authentic_engagement_bonus


def engagement_quality_score(overall_fake_risk_score: float | int | None,
                             features: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute the role-5 engagement-quality score.

    Parameters
    ----------
    overall_fake_risk_score:
        The 0-100 overall fake risk score produced by the detection
        stage. ``None`` is treated as 0.
    features:
        Optional feature dict used to compute the authentic bonus.
        Supported keys: ``diverse_comments_score``,
        ``context_relevant_comments_score``,
        ``stable_engagement_rate_score``,
        ``realistic_like_comment_ratio_score``,
        ``organic_source_diversity_score``. Each is expected in
        ``[0, 1]`` and the resulting bonus is capped at 10 points.
    """
    features = features or {}
    fake_risk = clamp(overall_fake_risk_score, 0, 100, default=0.0)
    bonus = authentic_engagement_bonus(features)
    score = clamp(100.0 - fake_risk + bonus, 0.0, 100.0)
    return {
        "engagement_quality_score": round(score, 2),
        "authentic_engagement_bonus": bonus,
        "overall_fake_risk_score": round(fake_risk, 2),
        "reasons": [
            "Engagement quality is reduced by overall fake risk"
            if fake_risk > 0 else "No fake-risk signal; engagement quality at baseline",
            *(["Authentic engagement bonus applied"] if bonus > 0 else []),
        ],
        "evidence": {
            "authentic_features": {name: ratio(features.get(name, 0))
                                    for name in ("diverse_comments_score", "context_relevant_comments_score",
                                                  "stable_engagement_rate_score", "realistic_like_comment_ratio_score",
                                                  "organic_source_diversity_score")},
        },
    }


__all__ = ["engagement_quality_score"]
