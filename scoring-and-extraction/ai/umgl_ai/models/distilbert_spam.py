"""DistilBERT-based spam classifier adapter.

The default backend. Wraps the existing
`mrm8488/bert-tiny-finetuned-sms-spam-detection` checkpoint that
the `SemanticEngine` already uses; exposes it as a `ModelSpec`
so the registry can route to it under the name `distilbert_spam`.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any

from .base import ModelInfo, ModelSpec

_CHECKPOINT = os.getenv(
    "UMGL_DISTILBERT_SPAM_MODEL",
    "mrm8488/bert-tiny-finetuned-sms-spam-detection",
)
_POSITIVE_LABELS = frozenset({"spam", "label_1"})


class DistilBertSpamAdapter:
    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._lock = Lock()

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="distilbert_spam",
            version=_CHECKPOINT,
            family="text-classifier",
            loaded=self._pipeline is not None,
            notes="default spam backend",
        )

    def probability(self, text: str) -> float:
        classifier = self._load()
        result = classifier(text, truncation=True, max_length=512, top_k=None)[0]
        positive = sum(
            float(item["score"])
            for item in result
            if str(item["label"]).lower() in _POSITIVE_LABELS
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


__all__ = ["DistilBertSpamAdapter"]
