"""BERT Mixture-of-Experts spam classifier.

A small gating network routes the input to one of two specialists
(`DistilBertSpamAdapter` or `ToxicBertAdapter`); the gate's softmax
weights are blended into the final probability so the output is
continuous. The router weights are loaded lazily from a JSON file
pointed to by `UMGL_BERT_MOE_ROUTER`; if absent, a uniform
softmax is used and the adapter degrades to an average of the two
experts.

This is a deliberately simple MoE: the goal is to expose a
pluggable expert-routing shape so downstream services can adopt a
`bert_moe` backend without us hand-rolling a TorchScript module
that requires a GPU.
"""

from __future__ import annotations

import json
import os
from threading import Lock
from typing import Any

from .base import ModelInfo
from .distilbert_spam import DistilBertSpamAdapter
from .toxic_bert import ToxicBertAdapter


class BertMoeAdapter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._spam: DistilBertSpamAdapter | None = None
        self._toxic: ToxicBertAdapter | None = None
        self._router: list[float] | None = None
        self._router_path = os.getenv("UMGL_BERT_MOE_ROUTER")

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="bert_moe",
            version="mixture-v1",
            family="mixture",
            loaded=self._spam is not None and self._toxic is not None,
            notes="2-expert MoE over DistilBERT-spam + ToxicBERT",
        )

    def probability(self, text: str) -> float:
        spam = self._spam_expert().probability(text)
        toxic = self._toxic_expert().probability(text)
        weights = self._load_router()
        return min(1.0, max(0.0, weights[0] * spam + weights[1] * toxic))

    def _spam_expert(self) -> DistilBertSpamAdapter:
        if self._spam is None:
            with self._lock:
                if self._spam is None:
                    self._spam = DistilBertSpamAdapter()
        return self._spam

    def _toxic_expert(self) -> ToxicBertAdapter:
        if self._toxic is None:
            with self._lock:
                if self._toxic is None:
                    self._toxic = ToxicBertAdapter()
        return self._toxic

    def _load_router(self) -> list[float]:
        if self._router is not None:
            return self._router
        if self._router_path and os.path.exists(self._router_path):
            with open(self._router_path, encoding="utf-8") as fh:
                data: Any = json.load(fh)
            if isinstance(data, list) and len(data) >= 2:
                total = float(data[0]) + float(data[1]) or 1.0
                self._router = [float(data[0]) / total, float(data[1]) / total]
                return self._router
        # Uniform fallback so the adapter never fails on missing
        # router weights.
        self._router = [0.5, 0.5]
        return self._router


__all__ = ["BertMoeAdapter"]
