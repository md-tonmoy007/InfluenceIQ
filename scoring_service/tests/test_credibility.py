from scoring_service.analysis.brand_safety_blocklist import scan_brand_safety
from scoring_service.analysis.credibility import calculate_credibility


def test_credibility_sparse_cap_and_fake_penalties() -> None:
    sparse = calculate_credibility(verified=True, professional_titles=["doctor"], authority_mentions=1,
        credentials=["MD"], sentiment_score=90, engagement_quality=90, data_source_count=1)
    assert sparse["credibility_score"] == 70 and sparse["confidence"] == "Low"
    risky = calculate_credibility(fake_comment_risk_score=90, fake_follower_risk_score=90,
        bot_behavior_risk_score=90, coordinated_engagement_risk_score=90, data_source_count=6)
    assert risky["credibility_score"] < 20


def test_brand_safety_flags_are_auditable() -> None:
    result = scan_brand_safety("A guaranteed profit scam and fake cure", "https://source.test")
    assert result["brand_safety_score"] == 40
    assert all(flag["source_url"] == "https://source.test" for flag in result["flags"])
    assert result["requires_llm_review"]
