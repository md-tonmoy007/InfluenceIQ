"""End-to-end integration tests for the scoring pipeline."""

from __future__ import annotations

from backend.pipeline.orchestrator.pipeline import run_role4_pipeline


def _make_candidate() -> dict:
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
    result = run_role4_pipeline(_make_candidate())
    assert type(result).__name__ == "Role4PipelineResult"


def test_final_score_in_range() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert 0 <= result.sub_scores.get("role4_trust_score", 0) <= 100


def test_score_version_present() -> None:
    result = run_role4_pipeline(_make_candidate())
    model_version = result.risk_score.get("model_version")
    assert model_version is not None
    assert "Role4-InfluenceScore" in str(model_version)


def test_sub_scores_are_present() -> None:
    result = run_role4_pipeline(_make_candidate())
    for key in (
        "relevance", "credibility", "engagement_quality", "sentiment",
        "brand_safety", "source_confidence", "overall_fake_risk", "role4_trust_score",
    ):
        assert key in result.sub_scores


def test_signal_scores_are_present() -> None:
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
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.grade, str) and result.grade
    assert isinstance(result.confidence, str) and result.confidence


def test_source_urls_present() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.source_urls, list)
    assert len(result.source_urls) > 0
    assert all(isinstance(u, str) and u for u in result.source_urls)


def test_positive_reasons_non_empty() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.positive_reasons, list)
    assert len(result.positive_reasons) > 0


def test_negative_reasons_is_list() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.negative_reasons, list)


def test_requires_human_review_is_bool() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.requires_human_review, bool)


def test_score_event_has_contact_info() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert result.score_event is not None
    assert "final_score" in result.score_event
    assert "grade" in result.score_event
    assert "confidence" in result.score_event


def test_signal_model_versions_is_dict() -> None:
    result = run_role4_pipeline(_make_candidate())
    assert isinstance(result.signal_model_versions, dict)
