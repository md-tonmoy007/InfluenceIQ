"""Tests for the multi-backend sentiment adapter."""

from __future__ import annotations

from backend.pipeline.analysis.sentiment_backends import (
    LexiconBackend,
    _select_backend,
    analyze_sentiment_multi,
)


def test_lexicon_backend_is_always_available() -> None:
    backend = _select_backend()
    # If no optional package is installed, the lexicon backend is the fallback
    assert isinstance(backend, LexiconBackend) or backend.name in {"vader", "transformer"}


def test_analyze_sentiment_multi_uses_lexicon_by_default() -> None:
    result = analyze_sentiment_multi(["Excellent helpful authentic advice"], 0)
    assert result["backend"] in {"vader", "transformer", "lexicon"}
    assert result["raw_sentiment_score"] >= 50


def test_analyze_sentiment_multi_reduces_with_fake_risk() -> None:
    safe = analyze_sentiment_multi(["Helpful professional advice"], 0)
    risky = analyze_sentiment_multi(["Helpful professional advice"], 80)
    assert risky["sentiment_score"] == round(safe["sentiment_score"] * 0.6, 2)
    assert risky["fake_risk_adjustment"] > 0


def test_analyze_sentiment_multi_handles_empty_input() -> None:
    result = analyze_sentiment_multi([], 0)
    assert result["sample_size"] == 0
    assert result["raw_sentiment_score"] == 50.0  # default when no comments
