"""Tests for the role-5 detection package."""

from __future__ import annotations

import pytest

from backend.pipeline.detection import (
    DetectionCategory,
    brand_safety_detection_from_scan,
    classify_detection,
    detect_bot_behavior,
    detect_brand_safety,
    detect_coordinated_engagement,
    detect_fake_comments,
    detect_fake_followers,
)


def test_classify_safe_when_low_fake_risk() -> None:
    decision = classify_detection(overall_fake_risk_score=10, data_source_count=5)
    assert decision.category == DetectionCategory.SAFE
    assert decision.risk_level == "LOW"
    assert not decision.requires_human_review


def test_classify_suspicious_band() -> None:
    decision = classify_detection(overall_fake_risk_score=30, data_source_count=5)
    assert decision.category == DetectionCategory.SUSPICIOUS
    assert decision.risk_level == "MEDIUM"


def test_classify_high_risk_band() -> None:
    decision = classify_detection(overall_fake_risk_score=50, data_source_count=5)
    assert decision.category == DetectionCategory.HIGH_RISK
    assert decision.risk_level == "HIGH"


def test_classify_bot_like_when_bot_score_high() -> None:
    decision = classify_detection(
        overall_fake_risk_score=70,
        bot_behavior_risk_score=80,
        data_source_count=5,
    )
    assert decision.category == DetectionCategory.BOT_LIKE
    assert decision.is_bot_like is True


def test_classify_fake_follower_when_follower_score_high() -> None:
    decision = classify_detection(
        overall_fake_risk_score=70,
        fake_follower_risk_score=80,
        data_source_count=5,
    )
    assert decision.category == DetectionCategory.FAKE_FOLLOWER
    assert decision.is_fake_follower is True


def test_classify_fake_comment_when_comment_score_high() -> None:
    decision = classify_detection(
        overall_fake_risk_score=70,
        fake_comment_risk_score=80,
        data_source_count=5,
    )
    assert decision.category == DetectionCategory.FAKE_COMMENT
    assert decision.is_fake_comment is True


def test_classify_spam_ring_when_coordinated_high() -> None:
    decision = classify_detection(
        coordinated_engagement_risk_score=85,
        data_source_count=5,
    )
    assert decision.category == DetectionCategory.SPAM_RING
    assert decision.is_spam_ring is True


def test_classify_brand_risk_when_safety_low() -> None:
    decision = classify_detection(brand_safety_score=30, data_source_count=5)
    assert decision.category == DetectionCategory.BRAND_RISK
    assert decision.risk_level == "SEVERE"


def test_classify_needs_human_review_when_sparse_and_fake() -> None:
    decision = classify_detection(overall_fake_risk_score=50, data_source_count=1)
    assert decision.category == DetectionCategory.NEEDS_HUMAN_REVIEW
    assert decision.requires_human_review is True


def test_classify_brand_safety_llm_review_propagates() -> None:
    decision = classify_detection(
        overall_fake_risk_score=10,
        data_source_count=5,
        brand_safety_requires_llm=True,
    )
    assert decision.requires_human_review is True


def test_detect_fake_comments_returns_evidence() -> None:
    result = detect_fake_comments(comments=["Amazing", "Amazing", "❤️❤️"])
    assert result["detector"] == "fake_comment"
    assert result["score"] > 0
    assert "High generic comment ratio" in result["reasons"]


def test_detect_fake_followers_engagement_mismatch() -> None:
    # Provide the full feature set so all five profile-anomaly and
    # growth-related signals fire. A 1M-follower account with no profile
    # pic, no bio, new account age, very low engagement, and a suspicious
    # handle should score well above 60.
    result = detect_fake_followers({
        "follower_count": 1_000_000,
        "following_count": 2,
        "engagement_rate": 0.0001,
        "account_age_days": 20,
        "post_count": 3,
        "profile_picture_present": False,
        "bio_present": False,
        "handle": "user999999",
        "follower_growth_anomaly_score": 1.0,
    })
    assert result["score"] > 60
    assert "Engagement does not match audience size" in result["reasons"]


def test_detect_bot_behavior_flags_uniformity() -> None:
    result = detect_bot_behavior({
        "posting_interval_uniformity": 1.0,
        "comment_interval_uniformity": 1.0,
        "same_text_reuse_ratio": 1.0,
        "engagement_burst_score": 1.0,
        "night_activity_ratio": 1.0,
        "activity_velocity_score": 1.0,
    })
    assert result["is_bot_like"] is True
    assert result["score"] == 100


def test_detect_coordinated_engagement_spam_ring() -> None:
    result = detect_coordinated_engagement({
        "repeated_commenter_cluster_score": 1,
        "duplicate_text_cluster_score": 1,
        "synchronized_activity_score": 1,
        "shared_hashtag_cluster_score": 1,
        "suspicious_account_overlap_score": 1,
    })
    assert result["is_spam_ring"] is True
    assert result["category"] == "SPAM_RING"


def test_detect_brand_safety_returns_flags_with_source() -> None:
    # Use a "severe" severity match so the brand-safety score is < 40
    # and the BRAND_RISK rule fires (per spec, brand_safety_score < 40).
    result = detect_brand_safety("posted a death threat and terror propaganda",
                                 source_url="https://source.test/x")
    assert result["is_brand_risk"] is True
    assert result["requires_llm_review"] is True
    assert all(flag["source_url"] == "https://source.test/x" for flag in result["flags"])


@pytest.mark.parametrize("category,expected_risk_level", [
    (DetectionCategory.SAFE, "LOW"),
    (DetectionCategory.SUSPICIOUS, "MEDIUM"),
    (DetectionCategory.HIGH_RISK, "HIGH"),
    (DetectionCategory.BOT_LIKE, "SEVERE"),
    (DetectionCategory.SPAM_RING, "SEVERE"),
    (DetectionCategory.BRAND_RISK, "SEVERE"),
    (DetectionCategory.NEEDS_HUMAN_REVIEW, "SEVERE"),
])
def test_risk_level_mapping(category: DetectionCategory, expected_risk_level: str) -> None:
    decision = classify_detection(overall_fake_risk_score=50, data_source_count=5)
    decision_dict = decision.as_dict()
    # The mapping is fixed for each category; verify it via _risk_level_for
    from backend.pipeline.detection.detection_classifier import _risk_level_for
    assert _risk_level_for(category) == expected_risk_level
    assert "detection_category" in decision_dict


def test_brand_safety_detection_from_scan_matches_detect_brand_safety() -> None:
    from backend.pipeline.analysis.brand_safety_blocklist import scan_brand_safety

    text = "posted a death threat and terror propaganda"
    url = "https://source.test/x"
    scan_result = scan_brand_safety(text, url)
    from_scan = brand_safety_detection_from_scan(scan_result, url)
    direct = detect_brand_safety(text, url)
    assert from_scan == direct
