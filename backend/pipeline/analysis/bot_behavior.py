from __future__ import annotations

from typing import Any

from backend.pipeline.model_classifiers import classify_with_model


def _clamp(value: Any) -> float:
    try: return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError): return 0.0


def score_bot_behavior(features: dict[str, Any]) -> dict[str, Any]:
    values = {name: _clamp(features.get(name, 0)) for name in (
        "posting_interval_uniformity", "comment_interval_uniformity", "same_text_reuse_ratio",
        "engagement_burst_score", "night_activity_ratio")}
    values["activity_velocity_score"] = _clamp(features.get("activity_velocity_score", features.get("activity_velocity", 0)))
    heuristic = 100 * _clamp(0.25 * values["posting_interval_uniformity"] + 0.20 * values["comment_interval_uniformity"]
        + 0.20 * values["same_text_reuse_ratio"] + 0.15 * values["engagement_burst_score"]
        + 0.10 * values["night_activity_ratio"] + 0.10 * values["activity_velocity_score"])
    model_result = None
    model_probability = features.get("model_bot_probability", features.get("model_bot_behavior_probability"))
    if model_probability is None:
        model_result = classify_with_model("bot_behavior", {"features": {**features, **values}})
        if model_result is not None:
            model_probability = model_result.risk_probability
    score = 0.60 * _clamp(model_probability) * 100 + 0.40 * heuristic if model_probability is not None else heuristic
    reasons = []
    if values["posting_interval_uniformity"] >= 0.6: reasons.append("Posting intervals are too uniform")
    if values["same_text_reuse_ratio"] >= 0.4: reasons.append("Repeated comments appear across posts")
    if values["engagement_burst_score"] >= 0.6: reasons.append("Engagement bursts occurred in a short time")
    if max(values["posting_interval_uniformity"], values["comment_interval_uniformity"], values["activity_velocity_score"]) >= 0.7:
        reasons.append("Activity rhythm resembles automation")
    evidence = {key: value for key, value in values.items() if value > 0}
    model_evidence = model_result.to_evidence() if model_result is not None else {}
    if model_result is not None:
        reasons.extend(model_result.reasons)
        evidence.update(model_evidence)
    return {"bot_behavior_risk_score": round(score, 2), "heuristic_bot_behavior_risk_score": round(heuristic, 2),
            "model_bot_probability": round(_clamp(model_probability), 4) if model_probability is not None else None,
            "model_provider": model_evidence.get("model_provider"), "model_name": model_evidence.get("model_name"),
            "reasons": list(dict.fromkeys(reasons)), "evidence": evidence}
