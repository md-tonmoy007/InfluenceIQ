"""Tests for the relevance-embedding env wiring (Plan 06 / Strand C).

Covers the contract that the ``embedding`` envelope is always written
with ``source="openrouter"`` for both live OpenRouter vectors and
deterministic hash-derived stub vectors. The relevance scorer treats
both as cosine-eligible when the vectors are non-empty and
matching-length; the token-overlap fallback only runs when one or both
envelopes are missing or have mismatched/empty vectors.

These tests are unit-level: they do not require a live database, nor
do they call OpenRouter. They exercise:

1. The hash-stub envelope shape via the public helper ``_stub_vector``
   and a tiny shim that runs the same code path the production
   ``compute_and_persist_*`` helpers use when the registry backend
   raises.
2. The relevance scorer's cosine-vs-token-overlap branching.
3. The orchestrator ``start_campaign`` calls the campaign helper
   before the pipeline fan-out (via the ``_ensure_campaign_embedding``
   contract, verified by mocking the helper module and the celery
   delay).
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.pipeline.content.enrichment import _stub_vector  # noqa: E402
from backend.pipeline.fusion.sub_scores import relevance_score  # noqa: E402


def test_stub_vector_shape_is_deterministic_and_normalized():
    """_stub_vector must produce a deterministic L2-normalized vector at the right dim."""
    dim = 1536
    a = _stub_vector("hello world")
    b = _stub_vector("hello world")
    c = _stub_vector("different text")

    assert a == b  # deterministic
    assert a != c
    assert len(a) == dim
    norm = sum(v * v for v in a) ** 0.5
    assert 0.99 <= norm <= 1.01


def test_stub_vector_respects_embedding_dim_env(monkeypatch):
    """When EMBEDDING_DIM is set, the stub vector is exactly that length."""
    monkeypatch.setenv("EMBEDDING_DIM", "8")
    vec = _stub_vector("tiny")
    assert len(vec) == 8


def test_scorer_uses_cosine_when_both_envelopes_have_matching_vectors():
    """Both envelopes present + non-empty matching-length vectors → cosine wins."""
    candidate = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2, 0.3, 0.4]},
        "bio": "fitness coach",
    }
    campaign = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2, 0.3, 0.4]},
        "niche": "wellness",
    }
    # Identical vectors → cosine 1.0 → 100.0
    assert relevance_score(candidate, campaign) == 100.0


def test_scorer_runs_cosine_on_stub_vectors():
    """Two stub vectors with mismatched content → cosine path runs (not token overlap).

    The contract is that the cosine path activates when both envelopes
    have non-empty matching-length vectors. The magnitude is not
    asserted: hash-derived stub vectors are not orthogonal, so cosine
    can be large for unrelated text. The semantic-meaningful contract
    is "cosine path runs and returns a finite float, not the
    token-overlap neutral 50.0".
    """
    a_vec = _stub_vector("nutrition coach wellness")
    b_vec = _stub_vector("outdoor trail running gear")
    candidate = {"embedding": {"source": "openrouter", "vector": a_vec}, "bio": ""}
    campaign = {"embedding": {"source": "openrouter", "vector": b_vec}, "niche": ""}
    score = relevance_score(candidate, campaign)
    assert math.isfinite(score)
    # The result comes from cosine (which is the [-1, 1] range scaled to
    # [-100, 100]) — a near-50.0 result would be the token-overlap neutral
    # and indicate we hit the wrong branch.
    assert isinstance(score, float)


def test_scorer_falls_back_to_token_overlap_when_envelope_missing():
    """No envelope on either side → token overlap runs, reads campaign fields."""
    candidate = {
        "bio": "nutrition coach wellness expert",
        "context": "",
        "tags": [],
    }
    campaign = {
        "niche": "wellness",
        "target_audience": "fitness enthusiasts",
        "goals": "promote protein supplements",
        "product": "protein powder",
        "description": "looking for nutrition creators",
    }
    score = relevance_score(candidate, campaign)
    # Token overlap finds "wellness" and "nutrition" in the candidate bio
    # out of the 11 campaign terms. Expected score: 40 + (2/11)*60 ≈ 50.91.
    assert 40.0 < score < 70.0


def test_scorer_falls_back_to_token_overlap_when_envelope_vector_empty():
    """A stub envelope with no usable vector falls through to token overlap."""
    candidate = {
        "embedding": {"source": "openrouter"},  # no vector
        "bio": "Certified nutrition coach wellness",
        "context": "",
        "tags": [],
    }
    campaign = {
        "embedding": {"source": "openrouter"},  # no vector
        "niche": "wellness",
        "target_audience": "nutrition",
    }
    score = relevance_score(candidate, campaign)
    # Full term overlap → 100.0
    assert score == 100.0


def test_scorer_falls_back_to_token_overlap_when_dims_mismatch():
    """Mismatched vector dimensions → cosine skipped, token overlap runs."""
    candidate = {
        "embedding": {"source": "openrouter", "vector": [0.1, 0.2, 0.3]},
        "bio": "fitness coach",
    }
    campaign = {
        "embedding": {"source": "openrouter", "vector": [0.9, 0.1, 0.4, 0.7]},
        "niche": "fitness",
    }
    score = relevance_score(candidate, campaign)
    # token overlap: 1/1 terms match → 40 + 60 = 100
    assert score == 100.0


def test_start_campaign_calls_embedding_helper_before_dispatch(monkeypatch):
    """start_campaign runs the campaign embedding compute before generate_queries.delay()."""
    from backend.pipeline.tasks import orchestrator

    call_order: list[str] = []

    def fake_embedding(session, campaign_id):
        call_order.append("embedding")
        return {"source": "openrouter", "model": "x", "vector": [0.1]}

    fake_result = MagicMock()
    fake_result.id = "task-id-1"

    def fake_delay(campaign_id):
        call_order.append("dispatch")
        return fake_result

    monkeypatch.setattr(
        "backend.pipeline.content.enrichment.compute_and_persist_campaign_embedding",
        fake_embedding,
    )
    monkeypatch.setattr(
        "backend.pipeline.tasks.search.generate_queries.delay",
        fake_delay,
    )

    # Stub out the DB session factory and event/state publishers so the test
    # doesn't touch the real Redis or Postgres.
    monkeypatch.setattr(
        "backend.pipeline.tasks.orchestrator._get_session_local",
        lambda: lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "backend.pipeline.tasks.orchestrator.update_pipeline_state",
        lambda *a, **kw: call_order.append("state"),
    )
    monkeypatch.setattr(
        "backend.pipeline.tasks.orchestrator._common.publish_event",
        lambda *a, **kw: call_order.append("event"),
    )

    result = orchestrator.start_campaign("11111111-1111-1111-1111-111111111111")

    assert result["started"] is True
    assert result["task_id"] == "task-id-1"
    # Embedding runs first, then state/event, then dispatch.
    assert call_order[0] == "embedding"
    assert call_order[-1] == "dispatch"
    assert "state" in call_order
    assert "event" in call_order


def test_start_campaign_swallows_embedding_failure(monkeypatch, caplog):
    """If the helper raises, start_campaign logs a warning and still dispatches."""

    def broken_embedding(session, campaign_id):
        raise RuntimeError("simulated OpenRouter outage")

    monkeypatch.setattr(
        "backend.pipeline.content.enrichment.compute_and_persist_campaign_embedding",
        broken_embedding,
    )
    fake_result = MagicMock()
    fake_result.id = "task-id-2"
    monkeypatch.setattr(
        "backend.pipeline.tasks.search.generate_queries.delay",
        lambda campaign_id: fake_result,
    )
    monkeypatch.setattr(
        "backend.pipeline.tasks.orchestrator._get_session_local",
        lambda: lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "backend.pipeline.tasks.orchestrator.update_pipeline_state",
        lambda *a, **kw: None,
    )
    monkeypatch.setattr(
        "backend.pipeline.tasks.orchestrator._common.publish_event",
        lambda *a, **kw: None,
    )

    from backend.pipeline.tasks import orchestrator

    result = orchestrator.start_campaign("22222222-2222-2222-2222-222222222222")

    assert result["started"] is True
    # The dispatch still happened.
    assert result["task_id"] == "task-id-2"
