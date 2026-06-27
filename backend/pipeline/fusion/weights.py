"""Map campaign API weights into trust fusion weights."""

from __future__ import annotations

from backend.pipeline.fusion.trust import DEFAULT_POSITIVE_WEIGHTS


def campaign_weights_to_trust_weights(campaign_weights: dict | None) -> dict[str, float]:
    """Normalize campaign weights into the trust fusion key space."""
    defaults = dict(DEFAULT_POSITIVE_WEIGHTS)
    if not campaign_weights:
        return defaults

    mapped = {
        "relevance": float(campaign_weights.get("relevance", defaults["relevance"])),
        "credibility": float(campaign_weights.get("credibility", defaults["credibility"])),
        "engagement_quality": float(
            campaign_weights.get("engagement", campaign_weights.get("engagement_quality", defaults["engagement_quality"]))
        ),
        "sentiment": float(campaign_weights.get("sentiment", defaults["sentiment"])),
        "brand_safety": float(campaign_weights.get("brand_safety", defaults["brand_safety"])),
        "source_confidence": float(
            campaign_weights.get("source_confidence", defaults["source_confidence"])
        ),
    }
    total = sum(max(0.0, value) for value in mapped.values())
    if total <= 0:
        return defaults
    return {key: value / total for key, value in mapped.items()}
