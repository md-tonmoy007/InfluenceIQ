"""DeBERTa-v3 spam classifier adapter.

DeBERTa is heavier than DistilBERT; this adapter attempts to load
the `microsoft/deberta-v3-base` family fine-tuned for SMS / Twitter
spam (env-overridable via `UMGL_DEBERTA_SPAM_MODEL`). When the
checkpoint is unreachable, the registry falls back to
`distilbert_spam` automatically.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any

from .base import ModelInfo

_CHECKPOINT = os.getenv(
    "UMGL_DEBERTA_SPAM_MODEL",
    "microsoft/deberta-v3-base",
)
_POSITIVE_LABELS = frozenset({"spam", "label_1", "1"})


class DebertaSpamAdapter:
    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._lock = Lock()

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="deberta_spam",
            version=_CHECKPOINT,
            family="text-classifier",
            loaded=self._pipeline is not None,
            notes="DeBERTa-v3 spam backend (falls back to distilbert_spam)",
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


__all__ = ["DebertaSpamAdapter"]
