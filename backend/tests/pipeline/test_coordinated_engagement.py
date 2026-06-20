from backend.pipeline.analysis.coordinated_engagement import score_coordinated_engagement


def test_coordinated_engagement_weighting_and_category() -> None:
    result = score_coordinated_engagement({"repeated_commenter_cluster_score": 1, "duplicate_text_cluster_score": 1,
        "synchronized_activity_score": 1, "shared_hashtag_cluster_score": 1, "suspicious_account_overlap_score": 1})
    assert result["coordinated_engagement_risk_score"] == 100
    assert result["category"] == "SPAM_RING"
