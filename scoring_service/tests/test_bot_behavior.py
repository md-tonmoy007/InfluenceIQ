from scoring_service.analysis.bot_behavior import score_bot_behavior


def test_bot_behavior_weighting() -> None:
    result = score_bot_behavior({"posting_interval_uniformity": 1, "comment_interval_uniformity": 1,
        "same_text_reuse_ratio": 1, "engagement_burst_score": 1, "night_activity_ratio": 1, "activity_velocity_score": 1})
    assert result["bot_behavior_risk_score"] == 100
    assert len(result["reasons"]) >= 3
