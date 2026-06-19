"""Toxic-BERT adapter.

Wraps the `unitary/toxic-bert` checkpoint that the existing
`SemanticEngine` already uses for toxicity scoring. The
`probability` method is the union of all the toxic labels Unity
exports (`toxic`, `severe_toxic`, `obscene`, `threat`, `insult`,
`identity_hate`).
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any

from .base import ModelInfo

_CHECKPOINT = os.getenv("UMGL_TOXIC_BERT_MODEL", "unitary/toxic-bert")
_TOXIC_LABELS = frozenset(
    {"toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"}
)


class ToxicBertAdapter:
    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._lock = Lock()

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="toxic_bert",
            version=_CHECKPOINT,
            family="text-classifier",
            loaded=self._pipeline is not None,
            notes="toxicity backend",
        )

    def probability(self, text: str) -> float:
        classifier = self._load()
        result = classifier(text, truncation=True, max_length=512, top_k=None)[0]
        positive = sum(
            float(item["score"])
            for item in result
            if str(item["label"]).lower() in _TOXIC_LABELS
        )
        return min(1.0, max(0.0, positive))

    def _load(self) -> Any:
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    from transformers import pipeline

                    self._pipeline = pipeline(
                        "text-classification",
                        model=_CHECKPOINT,
                        device_map="auto",
                    )
        return self._pipeline


__all__ = ["ToxicBertAdapter"]
