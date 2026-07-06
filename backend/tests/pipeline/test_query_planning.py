"""Tests for query planning — deterministc path, deduplication, platform
diversification, and optional LLM path.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.pipeline.tasks.search import (
    _build_llm_query_prompt,
    _build_query_set,
    _ensure_location_coverage,
    _ensure_platform_coverage,
    _generate_planned_queries,
    _jaccard_similarity,
    _llm_generate_queries,
    _normalize_tokens,
    _primary_locations,
    _top_query,
    dedupe_queries,
)

# ---------------------------------------------------------------------------
# _build_query_set — deterministic path
# ---------------------------------------------------------------------------


def test_generate_queries_deterministic() -> None:
    """Deterministic path produces a query mentioning the description."""
    payload = {
        "description": "Protein powder for fitness enthusiasts, increase brand awareness among men 25-40",
        "preferred_platforms": ["youtube", "instagram"],
    }
    queries = _build_query_set(payload)
    assert 1 <= len(queries) <= 5
    assert all(isinstance(q, str) and q for q in queries)
    assert any("protein powder" in q.lower() for q in queries)


def test_generate_queries_minimal_payload() -> None:
    """Fallback to a bare query when no description is provided."""
    queries = _build_query_set({"description": ""})
    assert len(queries) == 1
    assert queries[0] == "top influencers"


# ---------------------------------------------------------------------------
# _primary_locations
# ---------------------------------------------------------------------------


def test_primary_locations_single() -> None:
    locations = _primary_locations({"locations": ["singapore"]})
    assert locations == ["Singapore"]


def test_primary_locations_multiple_limited() -> None:
    locations = _primary_locations({"locations": ["singapore", "Kuala Lumpur", "New York"]})
    assert locations == ["Singapore", "Kuala Lumpur"]


def test_primary_locations_empty() -> None:
    assert _primary_locations({}) == []
    assert _primary_locations({"locations": []}) == []
    assert _primary_locations({"locations": ["", "  "]}) == []


def test_primary_locations_inferred_from_description_when_no_explicit_location() -> None:
    """A location only mentioned in the free-text description is still picked up."""
    payload = {"description": "I am launching my natural ghee, I need influencers in India for this"}
    assert _primary_locations(payload) == ["India"]


def test_primary_locations_explicit_takes_precedence_over_description() -> None:
    """An explicit locations list wins even if the description mentions another country."""
    payload = {"description": "launching in the USA too", "locations": ["singapore"]}
    assert _primary_locations(payload) == ["Singapore"]


def test_primary_locations_no_match_in_description() -> None:
    """No known country mentioned anywhere -> empty list, no false positive."""
    assert _primary_locations({"description": "protein powder for fitness enthusiasts"}) == []


def test_primary_locations_mixed_case() -> None:
    locations = _primary_locations({"locations": ["SINGAPORE", "new york", "Los Angeles"]})
    assert locations == ["Singapore", "New York"]


# ---------------------------------------------------------------------------
# _top_query
# ---------------------------------------------------------------------------


def test_top_query_full() -> None:
    assert _top_query("protein powder for fitness", location="Singapore") == (
        "top influencers in Singapore for protein powder for fitness"
    )


def test_top_query_no_location() -> None:
    assert _top_query("protein powder") == "top influencers for protein powder"


def test_top_query_no_description() -> None:
    assert _top_query("", location="Singapore") == "top influencers in Singapore"


def test_top_query_empty() -> None:
    assert _top_query("") == "top influencers"


# ---------------------------------------------------------------------------
# _build_query_set — location-aware variants
# ---------------------------------------------------------------------------


def test_build_query_set_with_location() -> None:
    payload = {
        "description": "protein powder for fitness enthusiasts",
        "locations": ["singapore"],
    }
    queries = _build_query_set(payload)
    assert len(queries) >= 1
    assert queries[0] == "top influencers in Singapore for protein powder for fitness enthusiasts"


def test_build_query_set_with_two_locations() -> None:
    payload = {
        "description": "protein powder for fitness enthusiasts",
        "locations": ["singapore", "kuala lumpur"],
    }
    queries = _build_query_set(payload)
    assert any("in Singapore" in q for q in queries)
    assert any("in Kuala Lumpur" in q for q in queries)
    assert not any("Singapore Kuala Lumpur" in q for q in queries)


def test_build_query_set_no_location_no_in_clause() -> None:
    payload = {"description": "tea for wellness"}
    queries = _build_query_set(payload)
    assert not any(" in " in q for q in queries)


def test_build_query_set_all_start_with_top_and_carry_description() -> None:
    payload = {
        "description": "protein powder, increase brand awareness among men 25-40",
        "preferred_platforms": [],
    }
    queries = _build_query_set(payload)
    assert len(queries) > 0
    assert all(q.startswith("top ") for q in queries)
    assert all("protein powder" in q for q in queries)


# ---------------------------------------------------------------------------
# _build_llm_query_prompt
# ---------------------------------------------------------------------------


def test_build_llm_query_prompt_contains_description_and_location() -> None:
    payload = {
        "description": "protein powder for fitness enthusiasts",
        "locations": ["singapore"],
    }
    prompt = _build_llm_query_prompt(payload)
    assert "Campaign: protein powder for fitness enthusiasts" in prompt
    assert "Target location(s): Singapore" in prompt
    assert "start with 'top' followed by a count" in prompt


def test_build_llm_query_prompt_no_location() -> None:
    payload = {"description": "tea for wellness"}
    prompt = _build_llm_query_prompt(payload)
    assert "Target location(s): (not specified)" in prompt


def test_build_llm_query_prompt_no_description() -> None:
    prompt = _build_llm_query_prompt({})
    assert "Campaign: (not specified)" in prompt


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
# _ensure_location_coverage
# ---------------------------------------------------------------------------


def test_location_coverage_appends_missing() -> None:
    """Queries missing the target location get it appended."""
    queries = ["top 10 food influencers youtube tiktok", "top 20 cooking influencers"]
    result = _ensure_location_coverage(queries, ["India"])
    assert all("india" in q.lower() for q in result)


def test_location_coverage_already_present_unchanged() -> None:
    """A query that already mentions the location is left untouched."""
    queries = ["top 10 food influencers in India"]
    result = _ensure_location_coverage(queries, ["India"])
    assert result == queries


def test_location_coverage_no_locations_no_change() -> None:
    """No target locations -> queries pass through unchanged."""
    queries = ["top 10 food influencers"]
    assert _ensure_location_coverage(queries, []) == queries


def test_location_coverage_multiple_locations_any_match_counts() -> None:
    """A query mentioning any one of several target locations is left alone."""
    queries = ["top 10 food influencers in Kuala Lumpur", "top 20 cooking influencers"]
    result = _ensure_location_coverage(queries, ["Singapore", "Kuala Lumpur"])
    assert result[0] == queries[0]
    assert "singapore" in result[1].lower()


def test_generate_planned_queries_forces_location_into_llm_output() -> None:
    """Even if the LLM ignores the location instruction, the location is forced in."""
    payload = {"description": "natural ghee", "locations": ["india"]}
    with patch(
        "backend.pipeline.tasks.search._llm_generate_queries",
        return_value=[
            "top 10 food influencers youtube tiktok",
            "top 20 cooking influencers",
            "top 50 healthy eating influencers",
        ],
    ):
        queries = _generate_planned_queries(payload)
    assert all("india" in q.lower() for q in queries)


def test_generate_planned_queries_forces_location_from_description_only() -> None:
    """The reported bug: location only in free-text description, no explicit field."""
    payload = {"description": "I am launching my natural ghee, I need influencers in India for this"}
    with patch(
        "backend.pipeline.tasks.search._llm_generate_queries",
        return_value=[
            "top 10 food influencers youtube tiktok",
            "top 20 cooking influencers",
            "top 50 healthy eating influencers",
            "top 10 Ayurveda influencers",
        ],
    ):
        queries = _generate_planned_queries(payload)
    assert all("india" in q.lower() for q in queries)


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
        "description": "protein powder, increase awareness with men",
        "preferred_platforms": [],
    }
    queries = _generate_planned_queries(payload)
    assert 1 <= len(queries) <= 5
    assert all(isinstance(q, str) and q for q in queries)


def test_planned_queries_applies_dedup() -> None:
    """The combined path applies dedup after generation."""
    payload = {"description": "tea for wellness", "preferred_platforms": []}
    queries = _generate_planned_queries(payload)
    # Verify no near-duplicates exist
    for i, a in enumerate(queries):
        for b in queries[i + 1:]:
            assert _jaccard_similarity(a, b) < 0.8


def test_planned_queries_prefers_platforms() -> None:
    """Every preferred platform appears in at least one query."""
    payload = {
        "description": "yoga mat, brand launch targeting women 20-35",
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
        "description": "protein powder, increase brand awareness among young athletes 18-30",
        "locations": ["singapore", "kuala lumpur"],
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
        payload = {"description": "vegan protein powder for fitness"}
        queries = _llm_generate_queries(payload)
        assert queries is not None
        assert len(queries) >= 3
        assert "vegan protein powder reviews" in queries


@patch("backend.pipeline.tasks.search._flag", return_value=True)
def test_llm_path_fallback_on_error(mock_flag: MagicMock) -> None:
    """When the LLM path raises, return None so the caller falls back."""
    with patch("backend.ml.models.registry.registry", side_effect=Exception("connection failed")):
        payload = {"description": "tea for wellness"}
        queries = _llm_generate_queries(payload)
        assert queries is None


@patch("backend.pipeline.tasks.search._flag", return_value=False)
def test_llm_path_flag_off(mock_flag: MagicMock) -> None:
    """When the flag is off, return None without attempting import."""
    queries = _llm_generate_queries({"description": "x"})
    assert queries is None
    mock_flag.assert_called_once_with("AI_AGENT_LLM_QUERY_PLANNING")


def test_normalize_tokens() -> None:
    """Token normalization works correctly."""
    assert _normalize_tokens("Hello World!") == {"hello", "world"}
    assert _normalize_tokens("") == set()
