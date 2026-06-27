"""Tests that pipeline outputs are deterministic across identical inputs.

Reason ordering, sub-score keys, and the explanation list must be
identical when the same candidate is processed twice.
"""

from __future__ import annotations

from backend.pipeline.orchestrator.pipeline import run_role4_pipeline

_CANDIDATE = {
    "influencer_id": "test-stable-001",
    "canonical_name": "Jane Doe",
    "platforms": {"instagram": "https://instagram.com/janedoe"},
    "profile_urls": ["https://instagram.com/janedoe"],
    "credentials": ["Wellness Coach"],
    "professional_titles": [],
    "mentions": [
        {
            "mention_id": "m-stable-1",
            "name": "Jane Doe",
            "source_url": "https://example.com/art1",
            "context": "Jane Doe is a wellness coach.",
            "platform": "web",
        },
        {
            "mention_id": "m-stable-2",
            "name": "Jane Doe",
            "source_url": "https://example.com/art2",
            "context": "Jane Doe discusses healthy living.",
            "platform": "web",
        },
    ],
    "data_source_count": 2,
    "source_url": "https://example.com/art1",
    "source_urls": ["https://example.com/art1", "https://example.com/art2"],
    "bio": "Wellness coach sharing health tips.",
    "content": "Jane Doe is a wellness coach with tips on healthy living.",
    "context": "Jane Doe discusses healthy living and wellness tips.",
    "comments": ["Great content!", "Very helpful advice."],
    "followers": 50000,
    "average_engagement": 2000,
    "verified": False,
}


def test_reasons_deterministic_order() -> None:
    """Reasons have identical order across two runs."""
    r1 = run_role4_pipeline(_CANDIDATE)
    r2 = run_role4_pipeline(_CANDIDATE)
    assert r1.positive_reasons == r2.positive_reasons
    assert r1.negative_reasons == r2.negative_reasons


def test_reasons_set_identical() -> None:
    """The set of reasons is the same across two runs."""
    r1 = run_role4_pipeline(_CANDIDATE)
    r2 = run_role4_pipeline(_CANDIDATE)
    assert set(r1.positive_reasons) == set(r2.positive_reasons)
    assert set(r1.negative_reasons) == set(r2.negative_reasons)


def test_sub_scores_deterministic() -> None:
    """Sub-score values are identical across two runs."""
    r1 = run_role4_pipeline(_CANDIDATE)
    r2 = run_role4_pipeline(_CANDIDATE)
    for key in r1.sub_scores:
        assert r1.sub_scores[key] == r2.sub_scores[key], f"Mismatch for sub_score {key}"


def test_signal_scores_deterministic() -> None:
    """Signal-score values are identical across two runs."""
    r1 = run_role4_pipeline(_CANDIDATE)
    r2 = run_role4_pipeline(_CANDIDATE)
    for key in r1.signal_scores:
        assert r1.signal_scores[key] == r2.signal_scores[key], f"Mismatch for signal_score {key}"


def test_score_version_deterministic() -> None:
    """Model version is identical across two runs."""
    r1 = run_role4_pipeline(_CANDIDATE)
    r2 = run_role4_pipeline(_CANDIDATE)
    assert r1.risk_score.get("model_version") == r2.risk_score.get("model_version")
    assert r1.risk_score.get("model_version") == r2.risk_score.get("model_version")


def test_source_urls_deterministic() -> None:
    """Source URL order is identical across two runs."""
    r1 = run_role4_pipeline(_CANDIDATE)
    r2 = run_role4_pipeline(_CANDIDATE)
    assert r1.source_urls == r2.source_urls
