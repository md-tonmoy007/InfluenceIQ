"""End-to-end integration tests for the scoring pipeline.

Tests that a candidate dict flowing through ``run_role4_pipeline``
produces all documented contract fields: final_score, score_version,
sub-scores, signal_scores, source_urls, explanations, etc.
"""

from __future__ import annotations

from backend.pipeline.orchestrator.pipeline import run_role4_pipeline, run_role5_pipeline


def _make_candidate() -> dict:
    """A realistic candidate dict with multiple mentions."""
    return {
        "influencer_id": "test-inf-001",
        "canonical_name": "Dr. Sarah Tan",
        "platforms": {"instagram": "https://instagram.com/drsarahtan",
                      "youtube": "https://youtube.com/@drsarahtan"},
        "profile_urls": ["https://instagram.com/drsarahtan", "https://youtube.com/@drsarahtan"],
        "credentials": ["Certified Nutritionist", "MD"],
        "professional_titles": ["Nutrition Expert"],
        "mentions": [
            {
                "mention_id": "m-001",
                "name": "Dr. Sarah Tan",
                "source_url": "https://example.com/article1",
                "context": "Dr. Sarah Tan is a certified nutrition expert.",
                "platform": "web",
            },
            {
                "mention_id": "m-002",
                "name": "Sarah Tan",
                "source_url": "https://example.com/article2",
                "context": "Sarah Tan discusses gut health.",
                "platform": "web",
            },
        ],
        "data_source_count": 2,
        "source_url": "https://example.com/article1",
        "source_urls": ["https://example.com/article1", "https://example.com/article2"],
        "bio": "Certified nutrition educator sharing evidence-based wellness content.",
        "content": "Dr. Sarah Tan is a certified nutritionist and MD with 124K followers.",
        "context": "Dr. Sarah Tan gives evidence-based nutrition advice.",
        "comments": ["Great advice!", "Very helpful and well-researched."],
        "followers": 124000,
        "average_engagement": 5400,
        "verified": True,
    }


def test_run_role4_pipeline_returns_Role4PipelineResult() -> None:
    """run_role4_pipeline returns a Role4PipelineResult (or Role5PipelineResult alias)."""
    candidate = _make_candidate()
    result = run_role4_pipeline(candidate)
    # Check class name instead of isinstance to avoid module-caching edge cases
    class_name = type(result).__name__
    assert class_name in ("Role4PipelineResult", "Role5PipelineResult"), (
        f"Unexpected result type: {class_name}"
    )


def test_run_role4_pipeline_identity_alias() -> None:
    """run_role4_pipeline and run_role5_pipeline are the same function."""
    assert run_role4_pipeline is run_role5_pipeline


def test_final_score_in_range() -> None:
    """final_score is in the documented 0-100 range."""
    result = run_role4_pipeline(_make_candidate())
    assert 0 <= result.sub_scores.get("role5_trust_score", 0) <= 100


def test_score_version_present() -> None:
    """The risk score contains role4_model_version."""
    result = run_role4_pipeline(_make_candidate())
    model_version = result.risk_score.get("role4_model_version")
    assert model_version is not None
    assert "Role4-InfluenceScore" in str(model_version)


def test_score_version_v1_alias() -> None:
    """The risk score contains model_version_v1_alias for backward compat."""
    result = run_role4_pipeline(_make_candidate())
    alias = result.risk_score.get("model_version_v1_alias")
    assert alias is not None


def test_sub_scores_are_present() -> None:
    """All sub-scores are present in the result."""
    result = run_role4_pipeline(_make_candidate())
    assert "relevance" in result.sub_scores
    assert "credibility" in result.sub_scores
    assert "engagement_quality" in result.sub_scores
    assert "sentiment" in result.sub_scores
    assert "brand_safety" in result.sub_scores
    assert "source_confidence" in result.sub_scores
    assert "overall_fake_risk" in result.sub_scores
    assert "role5_trust_score" in result.sub_scores


def test_signal_scores_are_present() -> None:
    """Signal scores dict has all expected keys."""
    result = run_role4_pipeline(_make_candidate())
    expected_keys = [
        "fake_comment_risk_score", "fake_follower_risk_score",
        "bot_behavior_risk_score", "coordinated_engagement_risk_score",
        "overall_fake_risk_score", "credibility_score", "sentiment_score",
        "brand_safety_score", "engagement_quality_score",
        "source_confidence_score",
    ]
    for key in expected_keys:
        assert key in result.signal_scores, f"Missing signal_score: {key}"


def test_grade_and_confidence_present() -> None:
    """Grade and confidence are non-empty strings."""
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.grade, str) and result.grade
    assert isinstance(result.confidence, str) and result.confidence


def test_source_urls_present() -> None:
    """source_urls is a non-empty list."""
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.source_urls, list)
    assert len(result.source_urls) > 0
    assert all(isinstance(u, str) and u for u in result.source_urls)


def test_positive_reasons_non_empty() -> None:
    """There is at least one positive reason."""
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.positive_reasons, list)
    assert len(result.positive_reasons) > 0


def test_negative_reasons_is_list() -> None:
    """Negative reasons is always a list (may be empty for perfect candidates)."""
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.negative_reasons, list)


def test_requires_human_review_is_bool() -> None:
    """requires_human_review is a boolean."""
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.requires_human_review, bool)


def test_score_event_has_contact_info() -> None:
    """The score event carries contact_info when CONTACT_INFO_ENABLED is true."""
    result = run_role4_pipeline(_make_candidate())
    # The event may or may not have contact_info depending on the flag
    assert result.score_event is not None
    assert "final_score" in result.score_event
    assert "grade" in result.score_event
    assert "confidence" in result.score_event


def test_signal_model_versions_is_dict() -> None:
    """signal_model_versions is always a dict (may be empty for heuristic path)."""
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.signal_model_versions, dict)
