from scoring_service.analysis.sentiment import analyze_sentiment


def test_sentiment_is_reduced_by_fake_risk() -> None:
    raw = analyze_sentiment(["Excellent helpful authentic advice"], 0)
    adjusted = analyze_sentiment(["Excellent helpful authentic advice"], 80)
    assert adjusted["sentiment_score"] == raw["sentiment_score"] * 0.6
    assert adjusted["fake_risk_adjustment"] > 0
