"""Tests for the semantic relevance scorer."""

from __future__ import annotations

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


def test_falls_back_when_candidate_stub():
    candidate = {
        "embedding": {"source": "stub", "vector": [0.1, 0.2]},
        "bio": "fitness coach wellness nutrition",
        "context": "",
        "tags": [],
    }
    campaign = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2]},
        "niche": "wellness",
        "target_audience": "nutrition",
    }
    score = relevance_score(candidate, campaign)
    assert score == 100.0


def test_falls_back_when_campaign_stub():
    candidate = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2]},
        "bio": "fitness",
    }
    campaign = {
        "embedding": {"source": "stub", "vector": [0.1, 0.2]},
        "niche": "wellness",
        "description": "looking for wellness creators",
    }
    score = relevance_score(candidate, campaign)
    assert score == 40.0


def test_both_stub_falls_back_to_token_overlap():
    candidate = {
        "embedding": {"source": "stub"},
        "bio": "fitness coach",
        "context": "",
        "tags": [],
    }
    campaign = {
        "embedding": {"source": "stub"},
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
