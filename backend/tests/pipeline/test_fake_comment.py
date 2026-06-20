from backend.pipeline.analysis.fake_comment import score_fake_comments


def test_fake_comment_formula_and_model_blend() -> None:
    features = {"generic_comment_ratio": 1, "duplicate_comment_ratio": 1, "emoji_only_ratio": 1,
                "spam_keyword_ratio": 1, "link_spam_ratio": 1, "low_context_comment_ratio": 1, "aigc_probability": 1}
    assert score_fake_comments(features)["fake_comment_risk_score"] == 100
    blended = score_fake_comments({**features, "model_fake_probability": 0})
    assert blended["fake_comment_risk_score"] == 40


def test_comment_reasons_map_to_features() -> None:
    result = score_fake_comments(comments=["Amazing", "Amazing", "❤️❤️", "DM me https://spam.test"])
    assert result["fake_comment_risk_score"] > 30
    assert result["evidence"]
