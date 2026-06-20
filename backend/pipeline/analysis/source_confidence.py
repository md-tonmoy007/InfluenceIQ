"""Pipeline 15 - Source Confidence Score.

Source confidence is the role-5 measure of *how trustworthy the evidence
base* is, independent of the influencer's content. The score is in
``[0, 100]`` and is built from the supplied evidence map:

* 20 points per independent source (capped at 100).
* 10 points per verified source (capped at 40).
* 10 points for a usable profile URL.
* 10 points for complete metadata.
* -15 points for same-source repetition.

The score is then clamped to ``[0, 100]``.
"""

from __future__ import annotations

from typing import Any

from backend.pipeline.fusion.normalize import clamp


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def source_confidence_score(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute the source-confidence score and return the components.

    Parameters
    ----------
    evidence:
        Optional dict with any of the following keys:

        * ``data_source_count`` (int)        - total sources
        * ``independent_source_count`` (int) - distinct sources
        * ``verified_source_count`` (int)    - verified / authoritative sources
        * ``same_source_repetition`` (float) - 0..1 ratio of duplicates
        * ``profile_url_available`` (bool)
        * ``metadata_completeness`` (float)   - 0..1
    """
    evidence = evidence or {}
    independent = _safe_int(evidence.get("independent_source_count", evidence.get("data_source_count")))
    verified = _safe_int(evidence.get("verified_source_count"))
    repetition = _safe_float(evidence.get("same_source_repetition"))
    profile_url = bool(evidence.get("profile_url_available", evidence.get("profile_urls")))
    metadata = _safe_float(evidence.get("metadata_completeness"))

    independent_points = min(100, 20 * independent)
    verified_points = min(40, 10 * verified)
    profile_points = 10 if profile_url else 0
    metadata_points = 10 * max(0.0, min(1.0, metadata))
    repetition_penalty = 15 * max(0.0, min(1.0, repetition))

    raw = independent_points + verified_points + profile_points + metadata_points - repetition_penalty
    score = clamp(raw, 0.0, 100.0)

    return {
        "source_confidence_score": round(score, 2),
        "components": {
            "independent_sources": {"count": independent, "points": round(independent_points, 2)},
            "verified_sources": {"count": verified, "points": round(verified_points, 2)},
            "profile_url_available": profile_url,
            "metadata_completeness": round(metadata, 4),
            "same_source_repetition": round(repetition, 4),
            "repetition_penalty": round(repetition_penalty, 2),
        },
        "reasons": [
            f"{independent} independent source(s) contribute to confidence",
            f"Source confidence is "
            f"{'High' if score >= 70 else 'Medium' if score >= 40 else 'Low'}"
            f" with {score:.2f}/100",
        ],
        "evidence": evidence,
    }


__all__ = ["source_confidence_score"]
