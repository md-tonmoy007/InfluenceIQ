"""Tests for the role-5 end-to-end pipeline orchestrator and event helpers."""

from __future__ import annotations

import json

from backend.pipeline.events import IdentityMerged, InfluencerFound, ScoreCalculated
from backend.pipeline.fusion.versioning import MODEL_VERSION, MODEL_VERSION_ALIAS
from backend.pipeline.orchestrator import run_role5_pipeline
from backend.pipeline.orchestrator.pipeline import trust_grade_to_confidence


def test_pipeline_returns_full_contract_for_clean_candidate() -> None:
    candidate = {
        "influencer_id": "i-1",
        "name": "Dr Sarah Tan",
        "canonical_name": "Dr Sarah Tan",
        "platforms": {"instagram": "https://instagram.com/drsarahtan"},
        "profile_urls": ["https://instagram.com/drsarahtan"],
        "credentials": ["MD"],
        "professional_titles": ["doctor"],
        "authority_mentions": ["university"],
        "data_source_count": 4,
        "bio": "Helpful professional nutrition education",
        "bio_present": True,
        "profile_picture_present": True,
        "comments": ["Helpful authentic advice", "Great post"],
        "follower_count": 10000,
        "following_count": 500,
        "engagement_rate": 0.02,
        "verified": True,
        "diverse_comments_score": 1,
        "context_relevant_comments_score": 1,
        "mentions": [
            {"name": "Dr Sarah Tan", "source_url": "https://source.test/nutrition.html"}
        ],
    }
    result = run_role5_pipeline(candidate)
    payload = result.to_dict()

    # All required contract keys are present
    for key in (
        "influencer_id", "canonical_name", "platforms", "profile_urls",
        "credentials", "professional_titles", "mentions", "detection",
        "sub_scores", "signal_scores", "risk_score", "grade", "confidence",
        "data_source_count", "positive_reasons", "negative_reasons",
        "source_urls", "requires_human_review", "explanation", "score_event",
    ):
        assert key in payload, key

    # Risk score uses the canonical model version
    assert payload["risk_score"]["model_version"] in (MODEL_VERSION, MODEL_VERSION_ALIAS)

    # Sub-score contract matches the role-5 spec
    expected = {
        "relevance", "credibility", "engagement_quality", "sentiment",
        "brand_safety", "source_confidence", "fake_comment_risk",
        "fake_follower_risk", "bot_behavior_risk", "coordinated_engagement_risk",
        "overall_fake_risk", "role5_trust_score",
    }
    assert expected.issubset(payload["sub_scores"])

    # Detection payload is well-formed
    detection = payload["detection"]
    for key in (
        "detection_category", "risk_level", "is_fake_comment", "is_fake_follower",
        "is_bot_like", "is_spam_ring", "requires_human_review",
    ):
        assert key in detection

    # Output is JSON-serializable
    json.dumps(payload)


def test_pipeline_detects_brand_risk_and_sets_human_review() -> None:
    candidate = {
        "influencer_id": "i-2",
        "name": "Alex Stone",
        "bio": "Posted a death threat and terror propaganda on his feed.",
        "data_source_count": 3,
        "comments": ["love this"],
    }
    result = run_role5_pipeline(candidate)
    payload = result.to_dict()
    assert payload["detection"]["detection_category"] == "BRAND_RISK"
    assert payload["requires_human_review"] is True
    # The brand safety score must be carried through to the sub-score
    assert payload["sub_scores"]["brand_safety"] < 40


def test_pipeline_emits_score_event_with_required_fields() -> None:
    candidate = {
        "influencer_id": "i-3",
        "name": "Dr Sarah Tan",
        "data_source_count": 4,
        "comments": ["Helpful and authentic"],
        "credentials": ["MD"],
        "professional_titles": ["doctor"],
        "verified": True,
    }
    result = run_role5_pipeline(candidate)
    event = result.score_event
    for key in ("influencer_id", "overall_fake_risk", "detection_category",
                "risk_category", "final_score", "grade", "confidence"):
        assert key in event


def test_pipeline_flagged_bot_risk_for_automation_signals() -> None:
    candidate = {
        "influencer_id": "i-bot",
        "name": "Bot Account",
        "data_source_count": 5,
        "follower_count": 10000,
        "engagement_rate": 0.02,
        "posting_interval_uniformity": 1.0,
        "comment_interval_uniformity": 1.0,
        "same_text_reuse_ratio": 1.0,
        "engagement_burst_score": 1.0,
        "night_activity_ratio": 1.0,
        "activity_velocity_score": 1.0,
    }
    result = run_role5_pipeline(candidate)
    assert result.detection["is_bot_like"] is True
    assert result.detection["detection_category"] == "BOT_LIKE"


def test_trust_grade_to_confidence_thresholds() -> None:
    assert trust_grade_to_confidence(1, "A", {}) == "Low"
    assert trust_grade_to_confidence(3, "A", {}) == "Medium"
    assert trust_grade_to_confidence(6, "A", {}) == "High"


def test_pipeline_default_uses_v1_model_version() -> None:
    """With no ML_USE_*_V2 flags set, the orchestrator emits the v1
    model version, an empty signal_model_versions dict, and the v1
    alias alongside the canonical name."""
    candidate = {"influencer_id": "i-v1", "data_source_count": 4, "comments": ["ok"]}
    result = run_role5_pipeline(candidate)
    assert result.risk_score["model_version"] == MODEL_VERSION
    assert result.signal_model_versions == {}
    # The v1 alias key is always present in the payload so consumers
    # that only match the historical string keep working.
    assert result.risk_score.get("model_version_v1_alias") == "Role5-FakeSignal-v1"


def test_event_helpers_serialize() -> None:
    payload = InfluencerFound(name="Sarah Tan", platform="instagram",
                              source="https://source.test/nutrition.html").to_payload()
    assert payload == {"name": "Sarah Tan", "platform": "instagram",
                       "source": "https://source.test/nutrition.html"}

    payload = IdentityMerged(canonical_id="abc", merged_from=["a", "b"],
                             confidence=0.95).to_payload()
    assert payload["canonical_id"] == "abc"
    assert payload["merged_from"] == ["a", "b"]
    assert payload["confidence"] == 0.95

    payload = ScoreCalculated(
        influencer_id="i-1", overall_fake_risk=42.5,
        detection_category="HIGH_RISK", risk_category="high",
        final_score=58.0, grade="C", confidence="Medium",
    ).to_payload()
    assert payload["detection_category"] == "HIGH_RISK"
    assert payload["final_score"] == 58.0
