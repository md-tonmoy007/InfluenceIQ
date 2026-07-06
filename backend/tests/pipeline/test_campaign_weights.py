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


def test_campaign_weights_full_relevance_stays_full():
    weights = campaign_weights_to_trust_weights(
        {"relevance": 1.0, "credibility": 0, "engagement": 0, "sentiment": 0, "brand_safety": 0}
    )
    assert weights["relevance"] == 1.0
    assert all(weights.get(k, 0.0) == 0.0 for k in weights if k != "relevance")


def test_campaign_weights_explicit_source_confidence_respected():
    weights = campaign_weights_to_trust_weights(
        {
            "relevance": 0.3,
            "credibility": 0.3,
            "engagement": 0.1,
            "sentiment": 0.1,
            "brand_safety": 0.1,
            "source_confidence": 0.1,
        }
    )
    assert abs(weights["source_confidence"] - 0.1) < 0.001
    assert abs(sum(weights.values()) - 1.0) < 0.001
