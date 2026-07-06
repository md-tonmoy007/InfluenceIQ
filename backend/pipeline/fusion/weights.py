"""Map campaign API weights into trust fusion weights."""

from __future__ import annotations

from backend.pipeline.fusion.trust import DEFAULT_POSITIVE_WEIGHTS


def campaign_weights_to_trust_weights(campaign_weights: dict | None) -> dict[str, float]:
    """Normalize campaign weights into the trust fusion key space.

    When *campaign_weights* is ``None`` (campaign never customized
    weights), the full system default — including its
    ``source_confidence`` share — is returned unchanged. When a dict is
    supplied, every key the campaign didn't explicitly set is treated
    as 0, not silently backfilled from the system default: a campaign
    that sets ``relevance=1.0`` and nothing else must get 100%
    relevance, not ~87% after an uncontrollable dimension is mixed in.
    """
    defaults = dict(DEFAULT_POSITIVE_WEIGHTS)
    if not campaign_weights:
        return defaults

    mapped = {
        "relevance": float(campaign_weights.get("relevance", 0.0)),
        "credibility": float(campaign_weights.get("credibility", 0.0)),
        "engagement_quality": float(
            campaign_weights.get("engagement", campaign_weights.get("engagement_quality", 0.0))
        ),
        "sentiment": float(campaign_weights.get("sentiment", 0.0)),
        "brand_safety": float(campaign_weights.get("brand_safety", 0.0)),
        "source_confidence": float(campaign_weights.get("source_confidence", 0.0)),
    }
    total = sum(max(0.0, value) for value in mapped.values())
    if total <= 0:
        return defaults
    return {key: value / total for key, value in mapped.items()}
