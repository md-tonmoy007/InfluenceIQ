"""Tests for query planning — deterministc path, deduplication, platform
diversification, and optional LLM path.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.pipeline.tasks.search import (
    _build_query_set,
    _ensure_platform_coverage,
    _generate_planned_queries,
    _llm_generate_queries,
    _normalize_tokens,
    _jaccard_similarity,
    dedupe_queries,
)


# ---------------------------------------------------------------------------
# _build_query_set — deterministic path
# ---------------------------------------------------------------------------


def test_generate_queries_deterministic() -> None:
    """Deterministic path produces 3–5 queries for a typical campaign."""
    payload = {
        "product": "protein powder",
        "niche": "fitness",
        "goals": "increase brand awareness",
        "target_audience": "men 25-40",
        "preferred_platforms": ["youtube", "instagram"],
    }
    queries = _build_query_set(payload)
    assert 3 <= len(queries) <= 5
    assert all(isinstance(q, str) and q for q in queries)
    assert any("protein powder" in q for q in queries)
    assert any("fitness" in q for q in queries)


def test_generate_queries_minimal_payload() -> None:
    """Fallback to a default query when almost no fields are provided."""
    queries = _build_query_set({"product": "", "niche": ""})
    assert len(queries) == 1
    assert queries[0] == "trusted creator recommendations"


def test_generate_queries_deterministic_without_platforms() -> None:
    """No platform tagging when preferred_platforms is empty."""
    payload = {"product": "tea", "niche": "wellness", "preferred_platforms": []}
    queries = _build_query_set(payload)
    assert all("youtube" not in q.lower() for q in queries)


# ---------------------------------------------------------------------------
# dedupe_queries — near-duplicate removal
# ---------------------------------------------------------------------------


def test_dedupe_queries_identical() -> None:
    """Identical queries are deduplicated."""
    queries = ["fitness influencers youtube", "fitness influencers youtube"]
    assert dedupe_queries(queries) == ["fitness influencers youtube"]


def test_dedupe_queries_near_duplicates() -> None:
    """Queries with high token overlap are deduplicated."""
    # "fitness influencers men" and "fitness influencers women"
    # share 2/4 tokens = 0.5, which is below 0.8 threshold
    queries = ["fitness influencers men youtube", "fitness influencers men"]
    # These share 4/4 = 1.0 tokens, so they should be deduplicated
    queries_identical_tail = ["top fitness influencers for men youtube", "fitness influencers for men youtube"]
    assert len(dedupe_queries(queries)) == 2  # below threshold
    assert len(dedupe_queries(queries_identical_tail)) == 1  # above threshold


def test_dedupe_queries_distinct() -> None:
    """Distinct queries are kept."""
    queries = ["protein powder fitness influencers", "yoga for beginners"]
    assert dedupe_queries(queries) == queries


def test_dedupe_queries_threshold() -> None:
    """Threshold parameter controls how aggressive dedup is."""
    a = "fitness influencers for men"
    b = "fitness influencers for women"
    # At 0.5 threshold they'd match; at 0.9 they shouldn't
    assert len(dedupe_queries([a, b], threshold=0.4)) == 1
    assert len(dedupe_queries([a, b], threshold=0.9)) == 2


def test_dedupe_queries_empty_input() -> None:
    """Empty list returns empty list."""
    assert dedupe_queries([]) == []


# ---------------------------------------------------------------------------
# _ensure_platform_coverage
# ---------------------------------------------------------------------------


def test_platform_coverage_adds_missing() -> None:
    """Missing platforms get appended to the first untagged query."""
    queries = ["fitness influencers", "protein powder reviews"]
    result = _ensure_platform_coverage(queries, ["youtube"])
    assert any("youtube" in q for q in result)


def test_platform_coverage_already_covered() -> None:
    """If a platform is already mentioned, no change needed."""
    queries = ["fitness influencers youtube"]
    result = _ensure_platform_coverage(queries, ["youtube"])
    assert result == queries


def test_platform_coverage_empty_platforms() -> None:
    """No platforms -> no change."""
    queries = ["fitness influencers"]
    assert _ensure_platform_coverage(queries, []) == queries


def test_platform_coverage_multiple_platforms() -> None:
    """Multiple missing platforms each get added to a query."""
    queries = ["fitness influencers", "workout tips"]
    result = _ensure_platform_coverage(queries, ["youtube", "tiktok"])
    platform_count = sum(
        1 for q in result for p in ("youtube", "tiktok") if p in q.lower()
    )
    assert platform_count >= 2


# ---------------------------------------------------------------------------
# _generate_planned_queries — combined path
# ---------------------------------------------------------------------------


def test_planned_queries_fallback_to_deterministic() -> None:
    """When the LLM flag is off, fall back to deterministic path."""
    payload = {
        "product": "protein powder",
        "niche": "fitness",
        "goals": "awareness",
        "target_audience": "men",
        "preferred_platforms": [],
    }
    queries = _generate_planned_queries(payload)
    assert 1 <= len(queries) <= 5
    assert all(isinstance(q, str) and q for q in queries)


def test_planned_queries_applies_dedup() -> None:
    """The combined path applies dedup after generation."""
    payload = {"product": "tea", "niche": "wellness", "preferred_platforms": []}
    queries = _generate_planned_queries(payload)
    # Verify no near-duplicates exist
    for i, a in enumerate(queries):
        for b in queries[i + 1:]:
            assert _jaccard_similarity(a, b) < 0.8


def test_planned_queries_prefers_platforms() -> None:
    """Every preferred platform appears in at least one query."""
    payload = {
        "product": "yoga mat",
        "niche": "yoga",
        "goals": "brand launch",
        "target_audience": "women 20-35",
        "preferred_platforms": ["youtube", "instagram", "tiktok"],
    }
    queries = _generate_planned_queries(payload)
    for platform in ("youtube", "instagram", "tiktok"):
        assert any(platform in q.lower() for q in queries), (
            f"Platform {platform} not found in any query: {queries}"
        )


def test_planned_queries_max_five() -> None:
    """No more than 5 queries are returned."""
    payload = {
        "product": "protein powder",
        "niche": "fitness",
        "goals": "increase brand awareness among young athletes",
        "target_audience": "athletes 18-30",
        "preferred_platforms": ["youtube", "instagram", "tiktok", "twitter"],
    }
    queries = _generate_planned_queries(payload)
    assert len(queries) <= 5


# ---------------------------------------------------------------------------
# LLM path (mocked)
# ---------------------------------------------------------------------------


@patch("backend.pipeline.tasks.search._flag", return_value=True)
def test_llm_path_success(mock_flag: MagicMock) -> None:
    """When the LLM flag is on and the backend returns valid JSON, prefer LLM output."""
    mock_llm = MagicMock()
    mock_llm.predict_text.return_value = '["vegan protein powder reviews", "plant-based fitness creators", "best vegan supplements"]'

    mock_registry = MagicMock()
    mock_registry.resolve_name.return_value = "llm"
    mock_registry.get.return_value = mock_llm

    with patch("backend.ml.models.registry.registry", return_value=mock_registry):
        payload = {"product": "protein powder", "niche": "vegan fitness"}
        queries = _llm_generate_queries(payload)
        assert queries is not None
        assert len(queries) >= 3
        assert "vegan protein powder reviews" in queries


@patch("backend.pipeline.tasks.search._flag", return_value=True)
def test_llm_path_fallback_on_error(mock_flag: MagicMock) -> None:
    """When the LLM path raises, return None so the caller falls back."""
    with patch("backend.ml.models.registry.registry", side_effect=Exception("connection failed")):
        payload = {"product": "tea", "niche": "wellness"}
        queries = _llm_generate_queries(payload)
        assert queries is None


@patch("backend.pipeline.tasks.search._flag", return_value=False)
def test_llm_path_flag_off(mock_flag: MagicMock) -> None:
    """When the flag is off, return None without attempting import."""
    queries = _llm_generate_queries({"product": "x", "niche": "y"})
    assert queries is None
    mock_flag.assert_called_once_with("AI_AGENT_LLM_QUERY_PLANNING")


def test_normalize_tokens() -> None:
    """Token normalization works correctly."""
    assert _normalize_tokens("Hello World!") == {"hello", "world"}
    assert _normalize_tokens("") == set()
