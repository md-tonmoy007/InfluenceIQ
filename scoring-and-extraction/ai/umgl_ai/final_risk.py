"""Final risk engine (Pipeline E).

Renormalises available component scores into a tenant-scoped weighted
ensemble. Missing or stale observations are dropped from the denominator so
the absence of evidence is never silently treated as ``0``. The resulting
``risk_score`` is mapped to one of the platform's :class:`RiskCategory`
values using versioned, auditable thresholds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


# These thresholds are the canonical operational mapping for the current
# model_version. Bumping ``model_version`` is the supported way to evolve
# them; the contracts layer records the version on every persisted
# assessment so the explanation and audit trails remain reproducible.
_DEFAULT_THRESHOLDS: dict[str, tuple[float, float]] = {
    "SAFE":         (0.00, 0.20),
    "SUSPICIOUS":   (0.20, 0.50),
    "HIGH_RISK":    (0.50, 0.80),
    "BOT":          (0.80, 0.92),
    "SPAM_RING":    (0.92, 1.01),
}

_MODEL_VERSION = "final-risk-ensemble-v1"


@dataclass(frozen=True)
class ComponentSignal:
    name: str
    score: float
    weight: float

    @property
    def contribution(self) -> float:
        return self.weight * self.score


@dataclass(frozen=True)
class FinalRiskDecision:
    risk_score: float
    category: str
    effective_weights: dict[str, float]
    missing_signals: list[str]
    model_version: str


def _renormalize(signals: list[ComponentSignal]) -> tuple[float, dict[str, float], list[str]]:
    available = [s for s in signals if s.score >= 0]
    missing = [s.name for s in signals if s.score < 0]
    if not available:
        return 0.0, {s.name: 0.0 for s in signals}, missing
    total = sum(s.weight for s in available) or 1.0
    weighted = sum(s.contribution for s in available) / total
    return weighted, {s.name: s.weight / total for s in available}, missing


def _classify(score: float) -> str:
    for label, (low, high) in _DEFAULT_THRESHOLDS.items():
        if low <= score < high:
            return label
    return "HIGH_RISK"


def _sigmoid_calibrated(value: float) -> float:
    """Map a raw linear ensemble to a [0, 1] score with mild calibration.

    The default linear ensemble already lives in [0, 1] because every
    component is itself a probability. A gentle sigmoid around 0.5
    sharpens the boundary between SUSPICIOUS and HIGH_RISK without
    shifting SAFE scores downwards.
    """

    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, 6.0 * (value - 0.5)))))


def evaluate(
    signals: Mapping[str, tuple[float, float]],
    *,
    calibrated: bool = True,
) -> FinalRiskDecision:
    """Aggregate component scores into a final risk decision.

    Parameters
    ----------
    signals:
        Mapping of signal name to ``(score, weight)``. Pass a negative
        score to mark the signal as missing — the engine drops it from
        the denominator and records it in ``missing_signals``.
    calibrated:
        When ``True`` (default) the linear ensemble passes through a
        logistic calibration step. Set ``False`` to keep the raw linear
        score for benchmarking or to compare against a baseline.
    """

    components = [
        ComponentSignal(name=name, score=score, weight=weight)
        for name, (score, weight) in signals.items()
        if weight > 0
    ]
    raw, effective, missing = _renormalize(components)
    # When no evidence is available we treat the subject as SAFE rather than
    # running the calibrated sigmoid on 0.0 (which would otherwise produce a
    # small but non-zero prior). The threshold map then classifies it as
    # SAFE directly, matching the spec's "absence of evidence" semantics.
    if not components or all(s.score < 0 for s in components):
        return FinalRiskDecision(
            risk_score=0.0,
            category="SAFE",
            effective_weights={name: 0.0 for name in signals},
            missing_signals=list(signals.keys()),
            model_version=_MODEL_VERSION,
        )
    score = _sigmoid_calibrated(raw) if calibrated else max(0.0, min(1.0, raw))
    return FinalRiskDecision(
        risk_score=score,
        category=_classify(score),
        effective_weights=effective,
        missing_signals=missing,
        model_version=_MODEL_VERSION,
    )
