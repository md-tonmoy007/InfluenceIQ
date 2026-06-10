"""GAT (Graph Attention Network) adapter.

`UMGL_GAT_CHECKPOINT` overrides the default checkpoint path. When
unset, the adapter uses the GnnBaseAdapter fallback.
"""

from __future__ import annotations

import os

from .gnn_base import GnnBaseAdapter


class GatAdapter(GnnBaseAdapter):
    name = "gat"
    family = "graph"

    def __init__(self) -> None:
        super().__init__()
        # Allow the more specific env var to win.
        env = os.getenv("UMGL_GAT_CHECKPOINT")
        if env:
            self._checkpoint = env


__all__ = ["GatAdapter"]
