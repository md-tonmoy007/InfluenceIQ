"""GCN (Graph Convolutional Network) adapter."""

from __future__ import annotations

import os

from .gnn_base import GnnBaseAdapter


class GcnAdapter(GnnBaseAdapter):
    name = "gcn"
    family = "graph"

    def __init__(self) -> None:
        super().__init__()
        env = os.getenv("UMGL_GCN_CHECKPOINT")
        if env:
            self._checkpoint = env


__all__ = ["GcnAdapter"]
