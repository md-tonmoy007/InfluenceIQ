"""Pipeline 13 - Brand Safety Detection.

Wraps :mod:`backend.pipeline.analysis.brand_safety_blocklist`. The block
list is a deterministic pre-filter; the role-5 classifier treats any
severe flag as a brand-safety risk that the upstream LLM pass should
review.

Brand-safety score is in 0-100 (higher is safer); the risk signal in the
rest of the pipeline is ``100 - brand_safety_score``.
"""

from __future__ import annotations

from typing import Any

from backend.pipeline.analysis.brand_safety_blocklist import scan_brand_safety


def brand_safety_detection_from_scan(result: dict[str, Any], source_url: str = "") -> dict[str, Any]:
    """Build the detection-shaped payload from an existing :func:`scan_brand_safety` result.

    Pure transform — does not re-scan. Use this when the caller already
    has a scan result (e.g. the orchestrator, which also needs the raw
    scan for cap/reason logic) to avoid running the block-list (and any
    model classifier behind ``ROLE5_USE_MODEL_CLASSIFIERS``) twice over
    the same text.
    """
    severe = any(flag.get("severity") == "severe" for flag in result.get("flags", []))
    return {
        "detector": "brand_safety",
        "score": float(result.get("brand_safety_score", 100.0)),
        "risk_score": float(result.get("brand_safety_risk_score", 0.0)),
        "is_brand_risk": float(result.get("brand_safety_score", 100.0)) < 40 or severe,
        "requires_llm_review": bool(result.get("requires_llm_review")),
        "reasons": list(result.get("reasons", [])),
        "flags": list(result.get("flags", [])),
        "matches": result.get("matches", {}),
        "risks": result.get("risks", {}),
        "source_url": result.get("source_url", source_url),
    }


def detect_brand_safety(text: str, source_url: str = "") -> dict[str, Any]:
    """Run brand-safety keyword scanning and produce a detection payload.

    The payload keeps the full set of block-list flags (category,
    severity, source URL, matched context) so the explanation panel can
    cite each evidence point.
    """
    result = scan_brand_safety(text, source_url)
    return brand_safety_detection_from_scan(result, source_url)
