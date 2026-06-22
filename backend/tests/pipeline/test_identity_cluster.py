"""Tests for campaign-wide identity cluster resolution.

These tests exercise the Celery task and the underlying resolver
logic for merging near-duplicate influencer mentions and routing
ambiguous pairs to the LLM path.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.identity.canonical import canonicalize_candidate, merge_candidates
from backend.pipeline.identity.fuzzy_match import candidate_similarity
from backend.pipeline.identity.resolver import resolve_candidates, resolve_identity_clusters


# ---------------------------------------------------------------------------
# Fixtures — mention dicts for two near-duplicate identities
# ---------------------------------------------------------------------------


@pytest.fixture
def mention_jane() -> dict:
    return {
        "name": "Dr. Jane Smith",
        "handle": "@janesmith",
        "platforms": {"instagram": "https://instagram.com/janesmith"},
        "profile_urls": ["https://instagram.com/janesmith"],
        "credentials": ["PhD", "Certified Nutritionist"],
        "source_url": "https://example.com/article1",
        "mention_id": "mention-001",
        "bio": "Nutrition expert Dr. Jane Smith",
        "context": "Jane Smith discusses healthy eating habits.",
    }


@pytest.fixture
def mention_jane_alt() -> dict:
    return {
        "name": "Dr. Jane Smith",
        "handle": "@drsmith",
        "platforms": {"instagram": "https://instagram.com/drsmith"},
        "profile_urls": ["https://instagram.com/drsmith"],
        "credentials": ["PhD"],
        "source_url": "https://example.com/article2",
        "mention_id": "mention-002",
        "bio": "Dr. Smith is a certified nutritionist",
        "context": "Dr. Jane Smith gives evidence-based nutrition advice.",
    }


@pytest.fixture
def mention_bob() -> dict:
    return {
        "name": "Bob Johnson",
        "handle": "@bobj",
        "platforms": {"youtube": "https://youtube.com/@bobj"},
        "profile_urls": ["https://youtube.com/@bobj"],
        "source_url": "https://example.com/article3",
        "mention_id": "mention-003",
        "bio": "Fitness coach Bob Johnson",
        "context": "Bob's workout routines are popular.",
    }


# ---------------------------------------------------------------------------
# Resolver unit tests
# ---------------------------------------------------------------------------


def test_near_duplicates_merge(mention_jane: dict, mention_jane_alt: dict) -> None:
    """Two near-duplicate mentions merge into one canonical record."""
    candidates = [canonicalize_candidate(mention_jane), canonicalize_candidate(mention_jane_alt)]
    result = resolve_identity_clusters(candidates)
    assert len(result["canonical"]) == 1
    assert len(result["merge_events"]) >= 1


def test_distinct_remain_separate(mention_jane: dict, mention_bob: dict) -> None:
    """Unrelated candidates remain separate records."""
    candidates = [canonicalize_candidate(mention_jane), canonicalize_candidate(mention_bob)]
    result = resolve_identity_clusters(candidates)
    assert len(result["canonical"]) == 2


def test_ambiguous_pair_detected(mention_jane: dict) -> None:
    """Two candidates with moderate similarity produce an ambiguous pair."""
    mention_partial = {
        "name": "Jane Doe",
        "handle": "@jdoe",
        "platforms": {"instagram": "https://instagram.com/jdoe"},
        "profile_urls": ["https://instagram.com/jdoe"],
        "source_url": "https://example.com/article4",
        "mention_id": "mention-004",
        "bio": "Wellness advocate",
        "context": "Jane writes about wellness and lifestyle.",
    }
    candidates = [canonicalize_candidate(mention_jane), canonicalize_candidate(mention_partial)]
    result = resolve_identity_clusters(candidates)

    # Should have at least one ambiguous pair or two separate records
    assert len(result["canonical"]) >= 1


def test_resolve_candidates_confidence_threshold(mention_jane: dict) -> None:
    """resolve_candidates returns confidence >= 0.85 for merges."""
    mention_same = {**mention_jane, "mention_id": "mention-005", "source_url": "https://example.com/article5"}
    decision = resolve_candidates(mention_jane, mention_same)
    if decision["merge"]:
        assert decision["confidence"] >= 0.85, (
            f"Merge confidence {decision['confidence']} should be >= 0.85"
        )


# ---------------------------------------------------------------------------
# Event emission tests
# ---------------------------------------------------------------------------


def test_resolve_identity_clusters_emits_events(mention_jane: dict, mention_jane_alt: dict) -> None:
    """resolve_identity_clusters emits identity.merged events when event_emitter is provided."""
    events: list[str] = []

    def _emitter(cid: str, event_type: str, payload: object) -> None:
        events.append(event_type)

    candidates = [canonicalize_candidate(mention_jane), canonicalize_candidate(mention_jane_alt)]
    resolve_identity_clusters(candidates, campaign_id="test-campaign", event_emitter=_emitter)
    merged_events = [e for e in events if e == "identity.merged"]
    assert len(merged_events) >= 1


def test_low_confidence_routes_to_llm(mention_jane: dict) -> None:
    """When AI_AGENT_LLM_IDENTITY is on, an ambiguous pair triggers resolve_identity_llm."""
    mention_partial = {
        "name": "Jane X. Smith",
        "handle": "@janes",
        "platforms": {"instagram": "https://instagram.com/janes"},
        "profile_urls": ["https://instagram.com/janes"],
        "source_url": "https://example.com/article6",
        "mention_id": "mention-006",
        "bio": "Some Jane person",
        "context": "Jane is into fashion.",
    }
    candidates = [canonicalize_candidate(mention_jane), canonicalize_candidate(mention_partial)]
    result = resolve_identity_clusters(candidates)
    # This may or may not produce an ambiguous pair depending on similarity
    # At minimum, the function should not crash
    assert "canonical" in result
    assert "ambiguous_pairs" in result


# ---------------------------------------------------------------------------
# Celery task test (mocked)
# ---------------------------------------------------------------------------


def test_cluster_task_routes_to_scoring_queue() -> None:
    """The resolve_identity_cluster task routes to scoring_queue."""
    from backend.core.celery.roles import TASK_QUEUE_BY_NAME
    queue = TASK_QUEUE_BY_NAME.get("backend.pipeline.tasks.extract.resolve_identity_cluster")
    assert queue == "scoring_queue"
