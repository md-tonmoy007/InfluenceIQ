"""Tests for the semantic relevance scorer.

Plan-06 semantics: both live OpenRouter vectors and deterministic
hash-derived stub vectors carry ``source="openrouter"``. Cosine runs
whenever both sides have a non-empty matching-length vector. The token
overlap path runs only when one or both envelopes are missing (or when
the vectors have mismatched dimensions / zero norm).
"""

from __future__ import annotations

import math

from backend.pipeline.fusion.sub_scores import _token_overlap_relevance, relevance_score


def test_cosine_similarity_happy_path():
    candidate = {
        "embedding": {
            "source": "openrouter",
            "vector": [0.1, 0.2, 0.3, 0.4],
        },
        "bio": "fitness coach",
    }
    campaign = {
        "embedding": {
            "source": "openrouter",
            "vector": [0.1, 0.2, 0.3, 0.4],
        },
    }
    score = relevance_score(candidate, campaign)
    assert score == 100.0


def test_stub_candidate_and_live_campaign_runs_cosine():
    """Both sides carry source='openrouter' now (live + stub), so cosine runs."""
    candidate = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2, 0.3, 0.4]},
        "bio": "fitness coach wellness nutrition",
        "context": "",
        "tags": [],
    }
    campaign = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2, 0.3, 0.4]},
        "niche": "wellness",
        "target_audience": "nutrition",
    }
    score = relevance_score(candidate, campaign)
    assert score == 100.0


def test_live_candidate_and_stub_campaign_runs_cosine():
    """Stub and live both use source='openrouter' now → cosine on both sides."""
    candidate = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2]},
        "bio": "fitness",
    }
    campaign = {
        "embedding": {"source": "openrouter", "vector": [0.9, 0.1]},
        "niche": "wellness",
        "description": "looking for wellness creators",
    }
    score = relevance_score(candidate, campaign)
    # dot / (|a| * |b|) = (0.09 + 0.02) / (sqrt(0.05) * sqrt(0.82)) ≈ 0.34
    expected = round((0.11 / (math.sqrt(0.05) * math.sqrt(0.82))) * 100.0, 2)
    assert score == expected


def test_stub_envelope_with_empty_vector_falls_back_to_token_overlap():
    """A stub envelope with no usable vector falls through to token overlap."""
    candidate = {
        "embedding": {"source": "openrouter"},
        "bio": "fitness coach",
        "context": "",
        "tags": [],
    }
    campaign = {
        "embedding": {"source": "openrouter"},
        "niche": "fitness",
    }
    score = relevance_score(candidate, campaign)
    assert score > 50.0


def test_no_embeddings_at_all():
    candidate = {"bio": "fitness coach", "context": "", "tags": []}
    campaign = {"niche": "fitness"}
    score = relevance_score(candidate, campaign)
    assert score > 50.0


def test_token_overlap_includes_all_campaign_fields():
    candidate = {
        "context": "fitness sports nutrition supplements health wellness",
        "bio": "fitness coach protein nutrition expert",
        "tags": [],
    }
    campaign = {
        "niche": "wellness",
        "target_audience": "fitness enthusiasts",
        "goals": "increase brand awareness for supplements",
        "product": "protein powder",
        "description": "looking for nutrition creators",
    }
    score = _token_overlap_relevance(candidate, campaign)
    assert score > 60.0


def test_token_overlap_empty_campaign():
    assert _token_overlap_relevance({"bio": "test"}, {}) == 50.0


def test_token_overlap_ignores_short_terms():
    candidate = {"bio": "AI expert in ML", "context": "", "tags": []}
    campaign = {"niche": "AI"}
    # "AI" has len=2, gets filtered; no terms remain → neutral
    score = _token_overlap_relevance(candidate, campaign)
    assert score == 50.0
