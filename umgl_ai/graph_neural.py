"""`GraphNeuralEngine`: registry-driven graph embeddings.

A thin wrapper that takes the same `GraphAnalysisRequest` shape
the existing `GraphEngine` consumes but, when the optional
`UMGL_GRAPH_NEURAL_ENABLED=true` is set, replaces the
NetworkX-based Louvain baseline with a GNN embedding produced by
the active registry backend (default: `graphsage`).

The Louvain community pass is kept regardless; the GNN embedding
is appended to the response so callers can see whether the
neural path actually contributed a non-fallback result.
"""

from __future__ import annotations

import os
from typing import Any

from .contracts import GraphAnalysisRequest, GraphAnalysisResponse
from .graph import GraphEngine
from .models.registry import registry


class GraphNeuralEngine:
    def __init__(self) -> None:
        self._baseline = GraphEngine()
        self._registry = registry()
        self._enabled = os.getenv("UMGL_GRAPH_NEURAL_ENABLED", "false").lower() == "true"

    def analyze(self, request: GraphAnalysisRequest) -> GraphAnalysisResponse:
        response = self._baseline.analyze(request)
        if not self._enabled:
            return response
        try:
            backend = self._registry.get(self._registry.resolve_name("graph"))
            embedder: Any = getattr(backend, "embed_graph", None)
            if embedder is None:
                return response
            nodes = [getattr(n, "id", str(n)) for n in request.nodes]
            edges = [
                (getattr(e, "source", ""), getattr(e, "target", ""))
                for e in request.edges
            ]
            embedding = embedder(nodes, edges)
            # Attach the embedding to the response without
            # changing the response dataclass shape; consumers
            # that care about embeddings read from the
            # response.metadata dict.
            response.metadata["graph_embedding"] = embedding
            response.metadata["graph_backend"] = backend.info().name
        except Exception:  # noqa: BLE001 — graph path is best-effort
            response.metadata["graph_backend_error"] = "graph embedder failed"
        return response


__all__ = ["GraphNeuralEngine"]
