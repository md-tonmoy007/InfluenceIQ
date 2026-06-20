"""`SemanticEngineV2`: registry-driven version of `SemanticEngine`.

The v1 engine constructs its three classifiers inline; v2 looks
them up by name through :mod:`backend.ml.models.registry`. The
public API is intentionally identical (`score(TextInferenceRequest)
-> SemanticScore`) so the FastAPI handler can swap engines without
touching the route.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .contracts import SemanticScore, TextInferenceRequest
from .models.registry import ModelRegistry, registry


class SemanticEngineV2:
    def __init__(self, registry_instance: ModelRegistry | None = None) -> None:
        self._registry = registry_instance or registry()

    def score(self, request: TextInferenceRequest) -> SemanticScore:
        spam = self._safe_probability("spam", request.text)
        toxicity = self._safe_probability("toxicity", request.text)
        aigc = self._safe_probability("aigc", request.text)
        semantic = float(np.average([spam, toxicity, aigc], weights=[0.4, 0.25, 0.35]))
        return SemanticScore(
            subject_id=request.subject_id,
            semantic_score=semantic,
            spam_probability=spam,
            toxicity_probability=toxicity,
            aigc_probability=aigc,
            model_versions={
                "spam": self._registry.resolve_name("spam"),
                "toxicity": self._registry.resolve_name("toxicity"),
                "aigc": self._registry.resolve_name("aigc"),
            },
        )

    def _safe_probability(self, slot: str, text: str) -> float:
        try:
            backend = self._registry.get(self._registry.resolve_name(slot))
            probability: Any = getattr(backend, "probability", None)
            if probability is None:
                return 0.0
            return float(probability(text))
        except Exception:  # noqa: BLE001 — registry is best-effort
            return 0.0


__all__ = ["SemanticEngineV2"]
