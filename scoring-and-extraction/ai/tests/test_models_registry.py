"""Tests for the new model registry and its backends.

The tests avoid touching the network (HuggingFace / Ollama) by
exercising the registry's fallback and stub paths. A real backend
that can load is allowed to be exercised if its optional
dependency is installed; the assertions are loose enough to
accommodate either.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from umgl_ai.models.base import ModelInfo
from umgl_ai.models.registry import ModelRegistry, registry


@pytest.fixture
def fresh_registry(monkeypatch: pytest.MonkeyPatch) -> ModelRegistry:
    monkeypatch.setenv("UMGL_SEMANTIC_BACKEND", "distilbert_spam")
    monkeypatch.setenv("UMGL_TOXICITY_BACKEND", "toxic_bert")
    monkeypatch.setenv("UMGL_AIGC_BACKEND", "roberta_aigc")
    monkeypatch.setenv("UMGL_LLM_BACKEND", "llama_explainer")
    monkeypatch.setenv("UMGL_GRAPH_BACKEND", "graphsage")
    return ModelRegistry()


def test_registry_resolves_known_names(fresh_registry: ModelRegistry) -> None:
    info = fresh_registry.resolve_name("spam")
    assert info == "distilbert_spam"
    info = fresh_registry.resolve_name("llm")
    assert info == "llama_explainer"


def test_registry_rejects_unknown_name(fresh_registry: ModelRegistry) -> None:
    with pytest.raises(KeyError):
        fresh_registry.get("not-a-real-backend")


def test_info_advertises_one_entry_per_slot(fresh_registry: ModelRegistry) -> None:
    items = fresh_registry.info()
    assert len(items) >= 5
    families = {item.family for item in items}
    assert "text-classifier" in families
    assert "llm" in families
    assert "graph" in families


def test_llama_explainer_stub_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a configured endpoint, the explainer returns a stub."""
    from umgl_ai.models.llama_explainer import LlamaExplainerAdapter

    monkeypatch.delenv("UMGL_LLM_ENDPOINT", raising=False)
    adapter = LlamaExplainerAdapter()
    import asyncio

    text = asyncio.run(adapter.predict_text("hello world"))
    assert text.startswith("[stub:")


def test_gnn_fallback_embedding_is_deterministic() -> None:
    from umgl_ai.models.gnn_base import _hash_embedding

    a = _hash_embedding("seed-a", 8)
    b = _hash_embedding("seed-a", 8)
    c = _hash_embedding("seed-b", 8)
    assert a == b
    assert a != c
    # L2-normalised: norm close to 1
    norm = sum(x * x for x in a) ** 0.5
    assert 0.99 <= norm <= 1.01


def test_registry_singleton_is_reusable() -> None:
    a = registry()
    b = registry()
    assert a is b
