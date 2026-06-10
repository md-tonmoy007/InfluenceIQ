"""Backend registry with env-driven selection and honest fallback.

Selection rules (highest priority first):

1. `UMGL_SEMANTIC_BACKEND` — chooses the spam-classifier backend.
2. `UMGL_LLM_BACKEND` — chooses the LLM explainer backend.
3. `UMGL_GRAPH_BACKEND` — chooses the GNN backend.

Each entry must be one of the registered names. When a backend
fails to load (missing optional dependency, unreachable HTTP
endpoint, etc.), the registry logs a warning and falls back to the
built-in default so the AI runtime stays up and the rest of the
pipeline keeps working.

Honest fallback is the contract: a backend that isn't reachable
must never crash a request. The /v1/models endpoint reflects the
current active backend and a `notes` field that explains any
degradation.
"""

from __future__ import annotations

import importlib
import logging
import os
import threading
from typing import Any

from .base import ModelInfo, ModelSpec

LOG = logging.getLogger(__name__)


_REGISTRY: dict[str, str] = {
    # text classifiers
    "distilbert_spam": "umgl_ai.models.distilbert_spam:DistilBertSpamAdapter",
    "deberta_spam": "umgl_ai.models.deberta_spam:DebertaSpamAdapter",
    "toxic_bert": "umgl_ai.models.toxic_bert:ToxicBertAdapter",
    "roberta_aigc": "umgl_ai.models.roberta_aigc:RobertaAigcAdapter",
    "bert_moe": "umgl_ai.models.bert_moe:BertMoeAdapter",
    # LLM explainer
    "llama_explainer": "umgl_ai.models.llama_explainer:LlamaExplainerAdapter",
    # GNN backends
    "gat": "umgl_ai.models.gat:GatAdapter",
    "graphsage": "umgl_ai.models.graphsage:GraphSageAdapter",
    "gcn": "umgl_ai.models.gcn:GcnAdapter",
    "ggt": "umgl_ai.models.ggt:GgtAdapter",
}

_DEFAULTS: dict[str, str] = {
    "spam": "distilbert_spam",
    "toxicity": "toxic_bert",
    "aigc": "roberta_aigc",
    "llm": "llama_explainer",
    "graph": "graphsage",
}


def _import_target(dotted: str) -> Any:
    module_path, _, attr = dotted.rpartition(":")
    if not module_path:
        raise ImportError(f"invalid registry target: {dotted!r}")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


class ModelRegistry:
    """Lazily constructs backend instances and caches them by name."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._instances: dict[str, ModelSpec] = {}
        self._fallbacks: dict[str, str] = {}

    def get(self, name: str) -> ModelSpec:
        with self._lock:
            cached = self._instances.get(name)
            if cached is not None:
                return cached
            target = _REGISTRY.get(name)
            if target is None:
                raise KeyError(f"unknown model backend: {name!r}")
            try:
                cls = _import_target(target)
                instance = cls()  # type: ignore[abstract]
            except Exception as exc:  # noqa: BLE001 — fall back honestly
                LOG.warning("backend %s failed to load: %s", name, exc)
                fallback = self._fallbacks.get(name) or self._default_for(name)
                if fallback == name:
                    raise
                self._fallbacks[name] = fallback
                return self.get(fallback)
            self._instances[name] = instance
            return instance

    def _default_for(self, name: str) -> str:
        # Map any text-classifier name to the distilbert default; this
        # gives the spam/toxicity/aigc slots a single shared fallback.
        if name in {
            "deberta_spam",
            "distilbert_spam",
            "toxic_bert",
            "roberta_aigc",
            "bert_moe",
        }:
            return "distilbert_spam"
        if name.startswith("llama") or name == "llama_explainer":
            return "llama_explainer"
        if name in {"gat", "graphsage", "gcn", "ggt"}:
            return "graphsage"
        return "distilbert_spam"

    def info(self) -> list[ModelInfo]:
        out: list[ModelInfo] = []
        # Always include the three default text-classifier slots,
        # then the LLM slot, then the active GNN backend.
        for slot, default in _DEFAULTS.items():
            try:
                backend_name = self.resolve_name(slot)
                backend = self.get(backend_name)
                info = backend.info()
                out.append(
                    ModelInfo(
                        name=info.name,
                        version=info.version,
                        family=info.family,
                        loaded=info.loaded,
                        notes=info.notes or f"slot={slot}",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                out.append(
                    ModelInfo(
                        name=default,
                        version="0.0.0",
                        family="unknown",
                        loaded=False,
                        notes=f"backend load failed: {exc}",
                    )
                )
        return out

    def resolve_name(self, slot: str) -> str:
        env_var = f"UMGL_{slot.upper()}_BACKEND"
        return os.getenv(env_var) or _DEFAULTS[slot]


_REGISTRY_SINGLETON = ModelRegistry()


def registry() -> ModelRegistry:
    return _REGISTRY_SINGLETON


__all__ = ["ModelRegistry", "registry", "ModelInfo", "ModelSpec"]
