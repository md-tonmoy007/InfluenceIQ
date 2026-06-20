from __future__ import annotations

from typing import Any

from .backends import ml_adapters as _ml_adapters
from .normalize import average_available, ratio, score


def _percent(value: Any) -> float | None:
    if value is None: return None
    number = float(value)
    return score(number * 100 if 0 <= number <= 1 else number)


# ---------------------------------------------------------------------------
# v2-aware variants. Each returns ``(score, used_v2, model_versions)`` so
# the orchestrator can record which layers fired the backend.ml path and
# surface the model provenance. The plain ``*_signal_score`` functions
# keep their existing signatures and delegate to the ``_with_provenance``
# variants, dropping the provenance.
# ---------------------------------------------------------------------------

SignalProvenance = tuple[float | None, bool, dict[str, str]]


def _drop_provenance(provenance: SignalProvenance) -> float | None:
    score_value, _used, _versions = provenance
    return score_value


def semantic_signal_score(features: dict[str, Any]) -> float | None:
    return _drop_provenance(semantic_signal_score_with_provenance(features))


def semantic_signal_score_with_provenance(features: dict[str, Any]) -> SignalProvenance:
    v2_score, versions = _ml_adapters.semantic_v2_score(features, candidate=features)
    if v2_score is not None:
        return v2_score, True, versions
    return average_available([_percent(features.get(name)) for name in (
        "spam_probability", "toxicity_probability", "aigc_probability", "claim_mismatch_score",
        "propaganda_template_match", "repeated_talking_point_score")]), False, {}


def behavioral_signal_score(scores: dict[str, Any], features: dict[str, Any]) -> float | None:
    return _drop_provenance(behavioral_signal_score_with_provenance(scores, features))


def behavioral_signal_score_with_provenance(scores: dict[str, Any], features: dict[str, Any]) -> SignalProvenance:
    v2_score, versions = _ml_adapters.behavioral_v2_score(features, candidate=features)
    if v2_score is not None:
        return v2_score, True, versions
    return average_available([
        scores.get("fake_follower_risk_score"), scores.get("fake_comment_risk_score"), scores.get("bot_behavior_risk_score"),
        _percent(features.get("posting_interval_uniformity")), _percent(features.get("engagement_velocity_anomaly", features.get("activity_velocity_score"))),
        _percent(features.get("duplicate_comment_ratio")), _percent(features.get("night_activity_ratio")),
    ]), False, {}


def graph_proxy_score(features: dict[str, Any]) -> float | None:
    return _drop_provenance(graph_proxy_score_with_provenance(features))


def graph_proxy_score_with_provenance(features: dict[str, Any]) -> SignalProvenance:
    # Graph v2 is inert in v1; the flag is honoured above but no engine
    # call is made. Heuristic path always runs.
    return average_available([_percent(features.get(name)) for name in (
        "repeated_commenter_cluster_score", "duplicate_text_cluster_score", "suspicious_account_overlap_score",
        "shared_hashtag_cluster_score", "same_source_cluster_score")]), False, {}


def bot_ring_signal_score(scores: dict[str, Any], features: dict[str, Any]) -> float | None:
    return _drop_provenance(bot_ring_signal_score_with_provenance(scores, features))


def bot_ring_signal_score_with_provenance(scores: dict[str, Any], features: dict[str, Any]) -> SignalProvenance:
    # Bot-rings v2 is inert in v1; the flag is honoured above but no
    # engine call is made. Heuristic path always runs.
    evidence_names = ("repeated_commenter_cluster_score", "duplicate_text_cluster_score", "synchronized_activity_score",
                      "shared_hashtag_cluster_score", "suspicious_account_overlap_score", "confirmed_bot_overlap_score",
                      "amplifier_account_ratio", "coordinated_engagement_risk_score")
    if not any(features.get(name) is not None for name in evidence_names):
        return None, False, {}
    return average_available([
        scores.get("coordinated_engagement_risk_score"), _percent(features.get("confirmed_bot_overlap_score")),
        _percent(features.get("amplifier_account_ratio")), _percent(features.get("synchronized_activity_score")),
    ]), False, {}


def overall_fake_risk(scores: dict[str, Any]) -> float:
    return score(0.30 * float(scores.get("fake_comment_risk_score", 0))
                 + 0.25 * float(scores.get("fake_follower_risk_score", 0))
                 + 0.25 * float(scores.get("bot_behavior_risk_score", 0))
                 + 0.20 * float(scores.get("coordinated_engagement_risk_score", 0)))


def overall_risk_category(value: float) -> str:
    if value <= 20: return "SAFE"
    if value <= 40: return "SUSPICIOUS"
    if value <= 65: return "HIGH_RISK"
    if value <= 80: return "BOT_LIKE"
    return "SPAM_RING"


def authentic_engagement_bonus(features: dict[str, Any]) -> float:
    values = [ratio(features.get(name, 0)) for name in (
        "diverse_comments_score", "context_relevant_comments_score", "stable_engagement_rate_score",
        "realistic_like_comment_ratio_score", "organic_source_diversity_score")]
    return round(min(10.0, sum(values) / len(values) * 10), 2)
