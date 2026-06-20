import math

from .contracts import BehaviorFeatures, BehaviorScore


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


class BehavioralEngine:
    """Calibrated feature model; coefficients are versioned and auditable."""

    VERSION = "behavior-calibration-v1"

    def score(self, f: BehaviorFeatures) -> BehaviorScore:
        contributions = {
            "posting_frequency": 0.90 * _sigmoid((f.posts_per_hour - 8.0) / 3.0),
            "short_account_age": 0.70 * math.exp(-f.account_age_days / 30.0),
            "engagement_velocity": 0.75 * _sigmoid((f.engagement_velocity - 50.0) / 15.0),
            "follower_growth": 0.55 * _sigmoid((f.follower_growth_per_day - 100.0) / 40.0),
            "duplicate_comments": 1.10 * f.duplicate_comment_ratio,
            "uniform_intervals": 0.95 * math.exp(-4.0 * f.posting_interval_cv),
            "night_activity": 0.35 * f.night_activity_ratio,
            "long_sessions": 0.25 * _sigmoid((f.median_session_minutes - 360.0) / 90.0),
        }
        logit = -2.5 + sum(contributions.values())
        return BehaviorScore(
            subject_id=f.subject_id,
            behavior_score=_sigmoid(logit),
            feature_contributions=contributions,
            model_version=self.VERSION,
        )

