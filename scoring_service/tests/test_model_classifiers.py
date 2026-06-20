from __future__ import annotations

from scoring_service.analysis import (
    bot_behavior,
    brand_safety_blocklist,
    fake_comment,
    fake_follower,
    sentiment,
)
from scoring_service.model_classifiers import ModelClassification, model_classifiers_enabled


def _classification(task: str, probability: float, score: float = 50.0) -> ModelClassification:
    return ModelClassification(
        task=task,
        risk_probability=probability,
        score=score,
        confidence=0.9,
        categories=["model_category"],
        reasons=["model reason"],
        provider="test",
        model="test-model",
    )


def test_model_classifiers_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ROLE5_USE_MODEL_CLASSIFIERS", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert model_classifiers_enabled() is False


def test_fake_comment_uses_optional_model_probability(monkeypatch) -> None:
    monkeypatch.setattr(fake_comment, "classify_with_model", lambda task, payload: _classification(task, 0.0))
    result = fake_comment.score_fake_comments(
        {
            "generic_comment_ratio": 1,
            "duplicate_comment_ratio": 1,
            "emoji_only_ratio": 1,
            "spam_keyword_ratio": 1,
            "link_spam_ratio": 1,
            "low_context_comment_ratio": 1,
            "aigc_probability": 1,
        },
        ["Amazing"],
    )
    assert result["fake_comment_risk_score"] == 40
    assert result["model_provider"] == "test"
    assert "model reason" in result["reasons"]


def test_fake_follower_uses_optional_model_probability(monkeypatch) -> None:
    monkeypatch.setattr(fake_follower, "classify_with_model", lambda task, payload: _classification(task, 1.0))
    result = fake_follower.score_fake_followers({
        "follower_count": 10_000,
        "following_count": 500,
        "engagement_rate": 0.02,
        "expected_engagement_rate": 0.02,
    })
    assert result["fake_follower_risk_score"] == 60
    assert result["model_fake_follower_probability"] == 1.0


def test_bot_behavior_uses_optional_model_probability(monkeypatch) -> None:
    monkeypatch.setattr(bot_behavior, "classify_with_model", lambda task, payload: _classification(task, 1.0))
    result = bot_behavior.score_bot_behavior({})
    assert result["bot_behavior_risk_score"] == 60
    assert result["model_bot_probability"] == 1.0


def test_brand_safety_blends_model_risk(monkeypatch) -> None:
    monkeypatch.setattr(brand_safety_blocklist, "classify_with_model", lambda task, payload: _classification(task, 1.0))
    result = brand_safety_blocklist.scan_brand_safety("ordinary content", "https://source.test")
    assert result["brand_safety_score"] == 40
    assert result["brand_safety_risk_score"] == 60
    assert result["model_brand_safety_probability"] == 1.0
    assert result["requires_llm_review"] is True


def test_sentiment_uses_model_quality_score(monkeypatch) -> None:
    monkeypatch.setattr(sentiment, "classify_with_model", lambda task, payload: _classification(task, 0.1, 80.0))
    result = sentiment.analyze_sentiment(["Terrible scam"], 0)
    assert result["raw_sentiment_score"] == 80.0
    assert result["model_sentiment_quality_probability"] == 0.1
    assert result["model_provider"] == "test"
