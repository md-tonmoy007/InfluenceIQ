"""Pipeline 16 - Role 4 Final Trust Score.

The trust score is a 0-100 number that combines the positive sub-scores
(``relevance``, ``credibility``, ``engagement_quality``, ``sentiment``,
``brand_safety``, ``source_confidence``) with the overall fake-risk
penalty. Three hard caps prevent misleadingly high trust when
high-impact signals are present:

* ``overall_fake_risk_score > 80`` -> trust capped at 45.
* Severe brand-safety flag         -> trust capped at 40.
* ``data_source_count < 3``       -> trust capped at 70.

Grades: ``A+ 90..100``, ``A 80..89``, ``B 70..79``, ``C 60..69``,
``D 40..59``, ``F 0..39``.

The cap list is also returned so the explanation panel can show *why*
the trust was bounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.pipeline.fusion.normalize import clamp
from backend.pipeline.fusion.normalize import score as clamp_score

DEFAULT_POSITIVE_WEIGHTS: dict[str, float] = {
    "relevance": 0.20,
    "credibility": 0.20,
    "engagement_quality": 0.15,
    "sentiment": 0.15,
    "brand_safety": 0.15,
    "source_confidence": 0.15,
}

FAKE_PENALTY_WEIGHT: float = 0.50

GRADE_BANDS: list[tuple[float, str]] = [
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B"),
    (60.0, "C"),
    (40.0, "D"),
    (0.0, "F"),
]


def grade_for_trust(value: float) -> str:
    for threshold, grade in GRADE_BANDS:
        if value >= threshold:
            return grade
    return "F"


@dataclass(frozen=True)
class TrustResult:
    """The output of :func:`calculate_role4_trust`."""

    role4_trust_score: float
    grade: str
    positive_trust_score: float
    fake_risk_penalty: float
    caps: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "role4_trust_score": self.role4_trust_score,
            "grade": self.grade,
            "positive_trust_score": self.positive_trust_score,
            "fake_risk_penalty": self.fake_risk_penalty,
            "caps": list(self.caps),
            "weights": dict(self.weights),
        }


def _safe(value: Any, default: float = 50.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _positive_trust(sub_scores: dict[str, Any], weights: dict[str, float]) -> float:
    total = 0.0
    for layer, weight in weights.items():
        candidates = (
            f"{layer}_score",
            layer,
            layer.replace("_quality_score", "_quality") if layer == "engagement_quality" else None,
        )
        value = next((sub_scores.get(name) for name in candidates if name and name in sub_scores), None)
        total += weight * _safe(value)
    return clamp_score(total)


def calculate_role4_trust(
    sub_scores: dict[str, Any],
    *,
    data_source_count: int = 0,
    severe_brand_safety: bool = False,
    positive_weights: dict[str, float] | None = None,
    fake_penalty_weight: float = FAKE_PENALTY_WEIGHT,
) -> TrustResult:
    """Compute the final role-4 trust score with all documented caps."""
    weights = dict(positive_weights or DEFAULT_POSITIVE_WEIGHTS)
    positive = _positive_trust(sub_scores, weights)
    fake_risk = _safe(
        sub_scores.get("overall_fake_risk_score", sub_scores.get("overall_fake_risk", 0)),
        default=0.0,
    )
    penalty = fake_penalty_weight * fake_risk
    trust = clamp(positive - penalty, 0.0, 100.0)

    caps: list[str] = []
    if fake_risk > 80:
        trust = min(trust, 45.0)
        caps.append("High fake-risk cap applied (max 45)")
    if severe_brand_safety:
        trust = min(trust, 40.0)
        caps.append("Severe brand-safety cap applied (max 40)")
    if data_source_count < 3:
        trust = min(trust, 70.0)
        caps.append("Sparse-data cap applied (max 70)")

    if data_source_count < 3:
        multiplier = min(1.0, data_source_count / 3.0)
        trust = trust * multiplier
        caps.append(f"Sparse-data confidence multiplier (x{multiplier:.2f})")

    return TrustResult(
        role4_trust_score=round(trust, 2),
        grade=grade_for_trust(trust),
        positive_trust_score=round(positive, 2),
        fake_risk_penalty=round(penalty, 2),
        caps=caps,
        weights=weights,
    )


__all__ = [
    "DEFAULT_POSITIVE_WEIGHTS",
    "FAKE_PENALTY_WEIGHT",
    "GRADE_BANDS",
    "TrustResult",
    "calculate_role4_trust",
    "grade_for_trust",
]
