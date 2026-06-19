from scoring_service.analysis.fake_follower import score_fake_followers


def test_fake_follower_formula_detects_mismatch() -> None:
    result = score_fake_followers({"follower_count": 1_000_000, "following_count": 2, "account_age_days": 20,
        "post_count": 3, "engagement_rate": 0.0001, "profile_picture_present": False, "bio_present": False,
        "handle": "user999999", "follower_growth_anomaly_score": 1})
    assert result["fake_follower_risk_score"] >= 75
    assert "Engagement does not match audience size" in result["reasons"]
