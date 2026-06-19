"""Pipeline 10 - Renormalized Weighted Fusion.

The role-5 fusion is **renormalized** by default: when a layer is
missing its weight is dropped and the remaining weights are rescaled to
sum to one. The :class:`RenormalizedFusion` dataclass makes the
intermediate math explicit and auditable.

The default weights come from the previous UMGL-Forensics 5-layer
ensemble (see ``Role-5-Scoring.md``):

================  ======
semantic          0.20
behavioral        0.30
graph_proxy       0.20
bot_rings         0.20
brand_safety      0.10
================  ======

A layer is considered available if its score is not ``None`` and
matches the expected ``[0, 100]`` range. Scores outside the range are
clamped. The output of :func:`fuse` is a 0-1 number that downstream
risk categorisation consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from scoring_service.scoring.normalize import score as clamp_score

DEFAULT_WEIGHTS: dict[str, float] = {
    "semantic": 0.20,
    "behavioral": 0.30,
    "graph_proxy": 0.20,
    "bot_rings": 0.20,
    "brand_safety": 0.10,
}


@dataclass(frozen=True)
class RenormalizedFusion:
    """Result of a renormalized 5-layer fusion.

    Attributes
    ----------
    score:
        The fused 0-1 risk score.
    components:
        Per-layer component dict in the canonical UMGL shape.
    renormalized:
        ``True`` if any layer was missing and the remaining weights
        were rescaled.
    available_layers:
        Names of layers that contributed to the fusion.
    missing_layers:
        Names of layers that were missing.
    weight_total:
        Sum of the *original* weights for the available layers. Equal
        to ``sum(DEFAULT_WEIGHTS)`` when every layer is present.
    """

    score: float
    components: dict[str, dict[str, float]]
    renormalized: bool
    available_layers: list[str] = field(default_factory=list)
    missing_layers: list[str] = field(default_factory=list)
    weight_total: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "components": self.components,
            "renormalized": self.renormalized,
            "available_layers": list(self.available_layers),
            "missing_layers": list(self.missing_layers),
            "weight_total": round(self.weight_total, 4),
        }


def _component_payload(layer: str, value: float | None, weight: float,
                       total_weight: float) -> dict[str, float | bool | None]:
    available = value is not None
    effective = (weight / total_weight) if (available and total_weight > 0) else 0.0
    normalized = (clamp_score(value) / 100.0) if available else None
    contribution = (normalized * effective) if normalized is not None else 0.0
    return {
        "score": round(normalized, 4) if normalized is not None else None,
        "weight": round(effective, 4),
        "contribution": round(contribution, 4),
        "available": available,
    }


def fuse(components: Mapping[str, float | None],
         weights: Mapping[str, float] | None = None) -> RenormalizedFusion:
    """Fuse the supplied layer scores with the documented weights.

    Parameters
    ----------
    components:
        Mapping from layer name to a 0-100 score. ``None`` means the
        layer is unavailable. Unknown layer names are ignored.
    weights:
        Optional custom weight mapping. When ``None`` the
        :data:`DEFAULT_WEIGHTS` are used.
    """
    weights = dict(weights or DEFAULT_WEIGHTS)
    available_names: list[str] = []
    missing_names: list[str] = []
    total = 0.0
    for layer in weights:
        if layer in components and components[layer] is not None:
            available_names.append(layer)
            total += weights[layer]
        else:
            missing_names.append(layer)

    renormalized = bool(missing_names)
    output: dict[str, dict[str, float | bool | None]] = {}
    fused = 0.0
    for layer, weight in weights.items():
        payload = _component_payload(layer, components.get(layer), weight, total)
        output[layer] = payload
        if payload["contribution"]:
            fused += float(payload["contribution"])
    fused = round(max(0.0, min(1.0, fused)), 4)
    return RenormalizedFusion(
        score=fused,
        components={k: {kk: vv for kk, vv in v.items()} for k, v in output.items()},
        renormalized=renormalized,
        available_layers=available_names,
        missing_layers=missing_names,
        weight_total=round(total, 4),
    )


__all__ = ["DEFAULT_WEIGHTS", "RenormalizedFusion", "fuse"]
