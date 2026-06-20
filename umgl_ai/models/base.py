"""Model spec protocol for the AI runtime.

This module defines a small duck-typed protocol (`ModelSpec`) that
text and graph adapters must satisfy. The registry in
:mod:`umgl_ai.models.registry` picks a backend by name and falls
back to the existing DistilBERT/ToxicBERT/RoBERTa trio if a
requested backend is unavailable (no GPU, no HF token, missing
optional dependency, etc.).

The contract is deliberately minimal so that:

* DistilBERT-spam and friends (already shipped) can be wrapped
  without any changes — they already expose `probability(text)`.
* HTTP adapters (Llama 3.1 explainer, vLLM, Ollama) only need a
  `predict_text` async method.
* GNN adapters (GAT, GraphSAGE, GCN) can implement a separate
  `predict_graph` method and live in the same registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ModelInfo:
    """Lightweight metadata advertised by every backend.

    The fields are intentionally simple so that the registry can
    surface them through the `/v1/models` endpoint without leaking
    any framework-specific objects.
    """

    name: str
    version: str
    family: str  # one of: text-classifier, llm, graph, mixture
    loaded: bool = True
    notes: str = ""


class TextScorer(Protocol):
    """Probability-of-positive for a text input, in [0, 1]."""

    def probability(self, text: str) -> float: ...


class AsyncTextPredictor(Protocol):
    """Asynchronous text generation, used by the LLM explainer."""

    async def predict_text(self, prompt: str, **kwargs: Any) -> str: ...


class GraphEmbedder(Protocol):
    """Graph -> embedding; consumed by the Qdrant upsert path."""

    def embed_graph(self, nodes: list[Any], edges: list[Any]) -> list[float]: ...


@runtime_checkable
class ModelSpec(Protocol):
    """The union of all three protocols.

    A backend may implement any subset; the registry only calls
    methods that the backend advertises via :meth:`info`. This
    avoids forcing LLM and GNN adapters to expose a meaningless
    `probability` method.
    """

    def info(self) -> ModelInfo: ...


__all__ = [
    "ModelInfo",
    "ModelSpec",
    "TextScorer",
    "AsyncTextPredictor",
    "GraphEmbedder",
]
