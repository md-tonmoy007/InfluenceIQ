import os
from dataclasses import dataclass
from threading import Lock
from typing import Any

import numpy as np
from transformers import pipeline

from .contracts import SemanticScore, TextInferenceRequest


@dataclass(frozen=True)
class ModelSpec:
    name: str
    positive_labels: frozenset[str]


class ClassificationModel:
    """Lazy, thread-safe Transformers sequence-classification adapter."""

    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec
        self._pipeline: Any | None = None
        self._lock = Lock()

    def probability(self, text: str) -> float:
        classifier = self._load()
        result = classifier(text, truncation=True, max_length=512, top_k=None)[0]
        positive = sum(
            float(item["score"])
            for item in result
            if str(item["label"]).lower() in self.spec.positive_labels
        )
        return min(1.0, max(0.0, positive))

    def _load(self) -> Any:
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    self._pipeline = pipeline(
                        "text-classification",
                        model=self.spec.name,
                        device_map="auto",
                    )
        return self._pipeline


class SemanticEngine:
    def __init__(self) -> None:
        self.spam = ClassificationModel(
            ModelSpec(
                os.getenv("UMGL_SPAM_MODEL", "mrm8488/bert-tiny-finetuned-sms-spam-detection"),
                frozenset({"spam", "label_1"}),
            )
        )
        self.toxicity = ClassificationModel(
            ModelSpec(
                os.getenv("UMGL_TOXICITY_MODEL", "unitary/toxic-bert"),
                frozenset({"toxic", "label_1"}),
            )
        )
        self.aigc = ClassificationModel(
            ModelSpec(
                os.getenv("UMGL_AIGC_MODEL", "roberta-base-openai-detector"),
                frozenset({"fake", "label_1"}),
            )
        )

    def score(self, request: TextInferenceRequest) -> SemanticScore:
        spam = self.spam.probability(request.text)
        toxicity = self.toxicity.probability(request.text)
        aigc = self.aigc.probability(request.text)
        semantic = float(np.average([spam, toxicity, aigc], weights=[0.4, 0.25, 0.35]))
        return SemanticScore(
            subject_id=request.subject_id,
            semantic_score=semantic,
            spam_probability=spam,
            toxicity_probability=toxicity,
            aigc_probability=aigc,
            model_versions={
                "spam": self.spam.spec.name,
                "toxicity": self.toxicity.spec.name,
                "aigc": self.aigc.spec.name,
            },
        )

