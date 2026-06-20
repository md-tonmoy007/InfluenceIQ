"""Gated Graph Transformer (GGT) adapter.

Falls back to the hash-based embedding the same way the other GNN
adapters do.
"""

from __future__ import annotations

import os

from .gnn_base import GnnBaseAdapter


class GgtAdapter(GnnBaseAdapter):
    name = "ggt"
    family = "graph"

    def __init__(self) -> None:
        super().__init__()
        env = os.getenv("UMGL_GGT_CHECKPOINT")
        if env:
            self._checkpoint = env


__all__ = ["GgtAdapter"]
