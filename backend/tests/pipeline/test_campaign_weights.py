from __future__ import annotations

from backend.pipeline.fusion.weights import campaign_weights_to_trust_weights
from backend.pipeline.fusion.trust import DEFAULT_POSITIVE_WEIGHTS


def test_campaign_weights_to_trust_weights_defaults():
    weights = campaign_weights_to_trust_weights(None)
    assert weights == DEFAULT_POSITIVE_WEIGHTS


def test_campaign_weights_to_trust_weights_renormalizes():
    weights = campaign_weights_to_trust_weights(
        {
            "relevance": 0.4,
            "credibility": 0.2,
            "engagement": 0.2,
            "sentiment": 0.1,
            "brand_safety": 0.1,
        }
    )
    assert abs(sum(weights.values()) - 1.0) < 0.001
    assert weights["relevance"] > weights["sentiment"]
