"""Legacy fusion helpers kept for back-compat.

This module exposes small helpers that the orchestrator and Celery
adapter continue to import:

* :func:`canonical_risk_category` - maps a 0-1 fused score to a
  lowercase category string (``safe / suspicious / high / bot_like /
  spam_ring``).
* :data:`DEFAULT_RISK_WEIGHTS` - default layer weights (the authoritative
  copy lives in :mod:`backend.pipeline.fusion.fusion`).
"""

from __future__ import annotations

from backend.pipeline.fusion.normalize import score
from backend.pipeline.fusion.versioning import MODEL_VERSION

# Default weights carried over from the previous implementation. The
# authoritative copy lives in
# :data:`backend.pipeline.fusion.fusion.DEFAULT_WEIGHTS`.
# Kept here so any consumer that imported it from this module keeps
# working.
DEFAULT_RISK_WEIGHTS = {
    "semantic": 0.20,
    "behavioral": 0.30,
    "graph_proxy": 0.20,
    "bot_rings": 0.20,
    "brand_safety": 0.10,
}


def canonical_risk_category(value: float) -> str:
    """Map a 0-1 fused score to a lowercase category string.

    Bands are documented in ``Role-5-Scoring.md``:

    * ``<= 0.20`` -> ``safe``
    * ``<= 0.40`` -> ``suspicious``
    * ``<= 0.65`` -> ``high``
    * ``<= 0.80`` -> ``bot_like``
    * ``>  0.80`` -> ``spam_ring``
    """
    if value <= 0.20:
        return "safe"
    if value <= 0.40:
        return "suspicious"
    if value <= 0.65:
        return "high"
    if value <= 0.80:
        return "bot_like"
    return "spam_ring"


def grade_for_trust(trust: float) -> str:
    """Legacy grade helper. The authoritative copy is
    :func:`backend.pipeline.fusion.trust.grade_for_trust`."""
    if trust >= 90:
        return "A+"
    if trust >= 80:
        return "A"
    if trust >= 70:
        return "B"
    if trust >= 60:
        return "C"
    if trust >= 40:
        return "D"
    return "F"


# Re-exported for completeness; the orchestrator and trust formula both
# import the same string from :mod:`backend.pipeline.fusion.versioning`.
__all__ = [
    "DEFAULT_RISK_WEIGHTS",
    "MODEL_VERSION",
    "canonical_risk_category",
    "grade_for_trust",
    "score",
]
