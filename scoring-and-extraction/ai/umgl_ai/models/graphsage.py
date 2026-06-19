"""GraphSAGE adapter (default GNN backend)."""

from __future__ import annotations

import os

from .gnn_base import GnnBaseAdapter


class GraphSageAdapter(GnnBaseAdapter):
    name = "graphsage"
    family = "graph"

    def __init__(self) -> None:
        super().__init__()
        env = os.getenv("UMGL_GRAPHSAGE_CHECKPOINT")
        if env:
            self._checkpoint = env


__all__ = ["GraphSageAdapter"]
