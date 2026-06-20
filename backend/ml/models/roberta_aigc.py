"""RoBERTa AIGC detector adapter.

The existing `SemanticEngine` uses
`roberta-base-openai-detector` for AI-generated-text scoring. This
adapter exposes it under the registry name `roberta_aigc` so the
semantic engine can be configured to route AIGC scoring through
the registry without changing the rest of the pipeline.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Any

from .base import ModelInfo

_CHECKPOINT = os.getenv("UMGL_ROBERTA_AIGC_MODEL", "roberta-base-openai-detector")
_POSITIVE_LABELS = frozenset({"fake", "label_1"})


class RobertaAigcAdapter:
    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._lock = Lock()

    def info(self) -> ModelInfo:
        return ModelInfo(
            name="roberta_aigc",
            version=_CHECKPOINT,
            family="text-classifier",
            loaded=self._pipeline is not None,
            notes="AIGC detector backend",
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


__all__ = ["RobertaAigcAdapter"]
