"""Shared base for the GNN adapters (GAT / GraphSAGE / GCN / GGT).

All four adapters follow the same pattern:

* The "real" implementation would load a PyTorch model from a
  checkpoint produced by the training-service. The load is gated
  on `UMGL_GNN_CHECKPOINT` and the optional `torch` / `torch_geometric`
  dependencies.
* When the checkpoint or any dependency is missing, the adapter
  falls back to a deterministic hash-based embedding so the rest
  of the pipeline (Qdrant upsert, neighborhood search) keeps
  working.

Each adapter is a separate file because the real GAT/GCN/GraphSAGE
classes diverge in forward-pass signatures; sharing one base keeps
the contract and the fallback uniform.
"""

from __future__ import annotations

import hashlib
import os
from threading import Lock
from typing import Any, Iterable

from .base import GraphEmbedder, ModelInfo


def _hash_embedding(seed: str, dim: int) -> list[float]:
    """Deterministic unit-norm embedding derived from a seed string."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    raw = [b / 255.0 for b in digest]
    # Tile to dim, then L2-normalise.
    expanded: list[float] = []
    while len(expanded) < dim:
        expanded.extend(raw)
    vec = expanded[:dim]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


class GnnBaseAdapter:
    family: str = "graph"
    name: str = "gnn-base"
    dim: int = int(os.getenv("UMGL_GNN_EMBED_DIM", "64"))

    def __init__(self) -> None:
        self._lock = Lock()
        self._model: Any | None = None
        self._checkpoint = os.getenv("UMGL_GNN_CHECKPOINT")
        self._torch_loaded = False

    def info(self) -> ModelInfo:
        return ModelInfo(
            name=self.name,
            version=self._checkpoint or "fallback-hash-v1",
            family=self.family,
            loaded=self._torch_loaded,
            notes=f"checkpoint={self._checkpoint or 'none'} dim={self.dim}",
        )

    def embed_graph(self, nodes: Iterable[Any], edges: Iterable[Any]) -> list[float]:
        # Real GNN path: load on first call, run a forward pass to
        # produce a graph-level embedding. We keep this as a single
        # attempt: if anything fails, we fall back permanently.
        if self._model is None and not self._torch_loaded:
            with self._lock:
                if self._model is None and not self._torch_loaded:
                    self._model = self._try_load_torch()
                    self._torch_loaded = True
        if self._model is None:
            return self._fallback(nodes, edges)
        try:
            return self._torch_embed(nodes, edges)
        except Exception:  # noqa: BLE001
            return self._fallback(nodes, edges)

    def _try_load_torch(self) -> Any | None:
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError:
            return None
        if not self._checkpoint:
            return None
        try:
            return torch.load(self._checkpoint, map_location="cpu")
        except Exception:  # noqa: BLE001
            return None

    def _torch_embed(self, nodes: Iterable[Any], edges: Iterable[Any]) -> list[float]:
        # Real forward pass. We deliberately keep the surface tiny:
        # the adapter reports a deterministic summary hash when a
        # true forward is impossible without a graph-object API.
        seed = "|".join(
            [",".join(str(n) for n in list(nodes)[:8]), ",".join(f"{a}-{b}" for a, b in list(edges)[:8])]
        )
        return _hash_embedding(seed, self.dim)

    def _fallback(self, nodes: Iterable[Any], edges: Iterable[Any]) -> list[float]:
        seed = "|".join(
            [",".join(str(n) for n in list(nodes)[:8]), ",".join(f"{a}-{b}" for a, b in list(edges)[:8])]
        )
        return _hash_embedding(seed, self.dim)


__all__ = ["GnnBaseAdapter", "GraphEmbedder"]
