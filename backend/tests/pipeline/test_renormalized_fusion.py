"""Tests for the dedicated renormalized fusion and trust-formula modules."""

from __future__ import annotations

import pytest

from backend.pipeline.fusion.fusion import DEFAULT_WEIGHTS, fuse
from backend.pipeline.fusion.trust import (
    DEFAULT_POSITIVE_WEIGHTS,
    FAKE_PENALTY_WEIGHT,
    GRADE_BANDS,
    calculate_role5_trust,
    grade_for_trust,
)


def test_renormalized_fusion_partial_layer_set() -> None:
    result = fuse({"semantic": 80, "behavioral": 60, "graph_proxy": None,
                   "bot_rings": 40, "brand_safety": 20})
    assert result.renormalized is True
    assert result.missing_layers == ["graph_proxy"]
    assert result.available_layers == ["semantic", "behavioral", "bot_rings", "brand_safety"]
    # Effective weights must sum to 1
    assert round(sum(c["weight"] for c in result.components.values()), 3) == 1.0


def test_renormalized_fusion_full_layer_set() -> None:
    result = fuse({"semantic": 50, "behavioral": 50, "graph_proxy": 50,
                   "bot_rings": 50, "brand_safety": 50})
    assert result.renormalized is False
    assert result.missing_layers == []
    assert result.score == 0.5


def test_renormalized_fusion_all_missing_returns_zero() -> None:
    result = fuse({"semantic": None, "behavioral": None, "graph_proxy": None,
                   "bot_rings": None, "brand_safety": None})
    assert result.score == 0.0
    assert result.renormalized is True


def test_renormalized_fusion_clamps_out_of_range() -> None:
    # Values outside [0, 100] should be clamped to 100, not panic.
    result = fuse({"semantic": 250, "behavioral": -10, "graph_proxy": 50,
                   "bot_rings": 50, "brand_safety": 50})
    # Semantic clamped to 100, behavioral clamped to 0
    assert result.components["semantic"]["score"] == 1.0
    assert result.components["behavioral"]["score"] == 0.0


def test_trust_formula_perfect_score() -> None:
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 0,
    }, data_source_count=6)
    assert trust.role5_trust_score == 100
    assert trust.grade == "A+"
    assert trust.caps == []


def test_trust_formula_high_fake_risk_cap() -> None:
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 90,
    }, data_source_count=6)
    assert trust.role5_trust_score <= 45
    assert any("High fake-risk" in c for c in trust.caps)


def test_trust_formula_sparse_data_cap() -> None:
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 0,
    }, data_source_count=1)
    # Sparse-data cap (max 70) + confidence multiplier (x0.33) → 23.33
    assert trust.role5_trust_score == pytest.approx(23.33, abs=0.01)
    assert any("Sparse-data" in c for c in trust.caps)
    assert any("confidence multiplier" in c for c in trust.caps)


def test_trust_formula_sparse_data_multiplier_two_sources() -> None:
    """With 2 sources the multiplier is 2/3 ≈ 0.67."""
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 0,
    }, data_source_count=2)
    # Sparse-data cap (max 70) + confidence multiplier (x0.67) → 46.67
    assert trust.role5_trust_score == pytest.approx(46.67, abs=0.01)


def test_trust_formula_no_multiplier_with_three_sources() -> None:
    """With 3+ sources no multiplier is applied."""
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 0,
    }, data_source_count=3)
    assert trust.role5_trust_score == 100.0  # no caps, no multiplier


def test_trust_formula_severe_brand_safety_cap() -> None:
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 0,
    }, data_source_count=6, severe_brand_safety=True)
    assert trust.role5_trust_score == 40
    assert any("Severe brand-safety" in c for c in trust.caps)


def test_trust_formula_combined_caps() -> None:
    # All three caps fire + confidence multiplier → 40 * 0.33 = 13.33
    trust = calculate_role5_trust({
        "relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
        "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
        "overall_fake_risk_score": 90,
    }, data_source_count=1, severe_brand_safety=True)
    assert trust.role5_trust_score == pytest.approx(13.33, abs=0.01)
    assert len(trust.caps) == 4  # 3 caps + multiplier


def test_trust_formula_default_weights_and_constants() -> None:
    assert sum(DEFAULT_POSITIVE_WEIGHTS.values()) == 1.0
    assert FAKE_PENALTY_WEIGHT == 0.5
    assert GRADE_BANDS[0] == (90.0, "A+")


def test_grade_for_trust_all_bands() -> None:
    assert grade_for_trust(95) == "A+"
    assert grade_for_trust(85) == "A"
    assert grade_for_trust(75) == "B"
    assert grade_for_trust(65) == "C"
    assert grade_for_trust(50) == "D"
    assert grade_for_trust(20) == "F"
    assert grade_for_trust(0) == "F"


def test_renormalized_fusion_default_weights_sum_to_one() -> None:
    assert round(sum(DEFAULT_WEIGHTS.values()), 4) == 1.0
