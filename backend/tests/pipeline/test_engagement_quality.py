"""Tests for the role-5 engagement-quality and source-confidence modules."""

from __future__ import annotations

from backend.pipeline.analysis.engagement_quality import engagement_quality_score
from backend.pipeline.analysis.source_confidence import source_confidence_score


def test_engagement_quality_decreases_with_fake_risk() -> None:
    safe = engagement_quality_score(0)
    risky = engagement_quality_score(80)
    assert risky["engagement_quality_score"] < safe["engagement_quality_score"]
    assert safe["engagement_quality_score"] == 100.0
    assert risky["engagement_quality_score"] == 20.0


def test_engagement_quality_authentic_bonus_capped_at_10() -> None:
    # All five authentic features maxed out -> bonus should cap at 10.
    result = engagement_quality_score(50, {
        "diverse_comments_score": 1,
        "context_relevant_comments_score": 1,
        "stable_engagement_rate_score": 1,
        "realistic_like_comment_ratio_score": 1,
        "organic_source_diversity_score": 1,
    })
    assert result["authentic_engagement_bonus"] == 10.0
    # 100 - 50 + 10 = 60
    assert result["engagement_quality_score"] == 60.0


def test_engagement_quality_clamps_zero() -> None:
    # Fake risk above 100 should still produce 0 after clamping the
    # fake risk to 100, even with no authentic bonus.
    result = engagement_quality_score(200, {})
    assert result["engagement_quality_score"] == 0.0
    # The fake risk itself is recorded as the clamped value
    assert result["overall_fake_risk_score"] == 100.0


def test_source_confidence_low_with_one_source() -> None:
    result = source_confidence_score({"data_source_count": 1})
    assert result["source_confidence_score"] == 20.0
    assert result["components"]["independent_sources"]["count"] == 1


def test_source_confidence_high_with_verified_and_profile() -> None:
    result = source_confidence_score({
        "data_source_count": 4,
        "verified_source_count": 2,
        "profile_url_available": True,
        "metadata_completeness": 0.8,
        "same_source_repetition": 0.1,
    })
    # 80 (independent) + 20 (verified, capped at 40) + 10 (profile) + 8 (metadata) - 1.5 (repetition)
    assert 100.0 <= result["source_confidence_score"] <= 100.0
    assert result["components"]["verified_sources"]["count"] == 2


def test_source_confidence_penalises_repetition() -> None:
    baseline = source_confidence_score({"data_source_count": 4})
    repeated = source_confidence_score({"data_source_count": 4, "same_source_repetition": 1.0})
    assert repeated["source_confidence_score"] < baseline["source_confidence_score"]
    assert repeated["components"]["repetition_penalty"] == 15.0
