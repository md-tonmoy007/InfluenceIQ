from __future__ import annotations

from typing import Any

from celery import shared_task

from app.scoring.formula import calculate_final_score, confidence_for_sources, grade_for_score
from app.scoring.versioning import score_metadata
from app.services.pipeline_state import emit_event, update_state
from scoring_service.analysis.brand_safety_blocklist import scan_brand_safety
from scoring_service.events import ScoreCalculated
from scoring_service.pipeline import run_role5_pipeline
from scoring_service.scoring.backends.umgl_ai_adapters import explain_via_llm
from scoring_service.scoring.renormalized_fusion import fuse as fuse_layers
from scoring_service.scoring.risk_components import overall_risk_category
from scoring_service.scoring.role5_fusion import canonical_risk_category
from scoring_service.scoring.sub_scores import build_role5_scores
from scoring_service.scoring.versioning import MODEL_VERSION


def _source_count(sub_scores: dict[str, Any]) -> int:
    raw_count = sub_scores.get("data_source_count", sub_scores.get("source_count", 0))
    try:
        return max(0, int(raw_count))
    except (TypeError, ValueError):
        return 0


def _maybe_llm_explanation(influencer_id: str, result: dict) -> None:
    """Opt-in natural-language explanation via umgl_ai's LLMExplainer.

    Mutates ``result["explanation"]`` in place when the explainer
    actually produced text. When the flag is off, the explainer is not
    importable, or the call fails, ``result["explanation"]`` is left
    untouched (the orchestrator's deterministic summary stays).
    """
    factors: dict[str, float] = {}
    for key, value in (result.get("sub_scores") or {}).items():
        if isinstance(value, (int, float)):
            factors[key] = float(value)
    evidence_ids = result.get("source_urls") or []
    text = explain_via_llm(influencer_id, factors, evidence_ids=list(evidence_ids))
    if text:
        result["explanation"] = text


@shared_task(name="app.tasks.score.classify_brand_safety", bind=True)
def classify_brand_safety(self, campaign_id: str, content: dict) -> dict:
    """Keyword blocklist Pass 1 -> LLM Pass 2 classification handled by ai_agent_services.
    Returns {risks: {hate_speech, misinformation, scam, ...}, reasons[], source_url}."""
    text = " ".join(
        str(value)
        for value in (
            content.get("title", ""),
            content.get("content", ""),
            content.get("snippet", ""),
        )
    )
    result = scan_brand_safety(text, content.get("url") or content.get("source_url", ""))
    update_state(campaign_id, phase="score", brand_safety_checked=True)
    return result


@shared_task(name="app.tasks.score.score_influencer", bind=True)
def score_influencer(self, campaign_id: str, influencer_id: str, sub_scores: dict) -> dict:
    """Expose the stable task contract and delegate Role 5 scoring to scoring_service.

    The contract is unchanged from the original spec:

        score_influencer(campaign_id, influencer_id, sub_scores) -> dict

    Two execution paths:

    1. Legacy fast-path: when the five legacy sub-scores are already
       present we run the platform's classic ``calculate_final_score``
       helper. The output stays byte-identical with the previous
       behaviour so existing consumers are not affected.

    2. Role 5 full path: when only the per-layer signals are present we
       call :func:`scoring_service.pipeline.run_role5_pipeline` which
       runs every spec pipeline (extraction -> identity -> detection ->
       scoring -> explanation -> event payload) and returns the
       full backend/frontend contract.
    """
    required_scores = {"relevance", "credibility", "engagement", "sentiment", "brand_safety"}
    if required_scores.issubset(sub_scores):
        data_source_count = _source_count(sub_scores)
        raw_score, normalized_sub_scores = calculate_final_score(sub_scores)
        confidence, final_score = confidence_for_sources(data_source_count, raw_score)
        fusion = fuse_layers({
            "semantic": sub_scores.get("semantic_signal_score"),
            "behavioral": sub_scores.get("behavioral_signal_score", sub_scores.get("overall_fake_risk")),
            "graph_proxy": sub_scores.get("graph_proxy_score"),
            "bot_rings": sub_scores.get("bot_ring_signal_score"),
            "brand_safety": 100 - normalized_sub_scores["brand_safety"],
        })
        # Reconstruct the dict shape the downstream consumers expect
        # (the legacy role5_fusion.fuse_risk_components output). The
        # dataclass is the source of truth, the dict is for back-compat.
        risk = {
            "score": fusion.score,
            "risk_category": canonical_risk_category(fusion.score),
            "components": {
                layer: {
                    "score": payload["score"],
                    "weight": payload["weight"],
                    "contribution": payload["contribution"],
                    "available": payload["available"],
                }
                for layer, payload in fusion.components.items()
            },
            "renormalized": fusion.renormalized,
        }
        result = {
            "influencer_id": influencer_id, "final_score": final_score, "grade": grade_for_score(final_score),
            "confidence": confidence, "sub_scores": normalized_sub_scores, "risk_score": risk,
            "overall_fake_risk": float(sub_scores.get("overall_fake_risk", fusion.score * 100)),
            "overall_risk_category": overall_risk_category(float(sub_scores.get("overall_fake_risk", fusion.score * 100))),
            **score_metadata(data_source_count), "model_version": MODEL_VERSION,
        }
    else:
        candidate = {**sub_scores, "influencer_id": influencer_id}
        # Try the full Role 5 pipeline first; fall back to the legacy
        # build_role5_scores path if the candidate is too sparse for
        # the orchestrator to do anything useful.
        try:
            generated = run_role5_pipeline(candidate, sub_scores.get("campaign"))
            generated_dict = generated.to_dict()
            data_source_count = generated.data_source_count
            result = {
                "influencer_id": influencer_id,
                "final_score": generated.sub_scores["role5_trust_score"],
                "grade": generated.grade,
                "confidence": generated.confidence,
                "sub_scores": generated.sub_scores,
                "signal_scores": generated.signal_scores,
                "risk_score": generated.risk_score,
                "detection": generated.detection,
                "score_explanations": generated.score_explanations,
                "overall_fake_risk": generated.sub_scores["overall_fake_risk"],
                "overall_risk_category": generated.detection["detection_category"],
                "positive_reasons": generated.positive_reasons,
                "negative_reasons": generated.negative_reasons,
                "explanation": generated.explanation,
                "requires_human_review": generated.requires_human_review,
                "source_urls": generated.source_urls,
                **score_metadata(data_source_count),
                "model_version": generated.risk_score["model_version"],
            }
        except Exception:
            generated = build_role5_scores(candidate, sub_scores.get("campaign"))
            data_source_count = generated["data_source_count"]
            result = {
                "influencer_id": influencer_id, "final_score": generated["sub_scores"]["role5_trust_score"],
                "grade": generated["grade"], "confidence": generated["confidence"],
                "sub_scores": generated["sub_scores"], "risk_score": generated["risk_score"],
                "overall_fake_risk": generated["sub_scores"]["overall_fake_risk_score"],
                "overall_risk_category": generated["overall_risk_category"],
                "positive_reasons": generated["positive_reasons"], "negative_reasons": generated["negative_reasons"],
                "explanation": generated["summary"], "requires_human_review": generated["requires_human_review"],
                "analysis": generated["analysis"], **score_metadata(data_source_count), "model_version": MODEL_VERSION,
            }
    # Opt-in LLM explainer — only overwrites the explanation when the
    # umgl_ai explainer actually produced text. The orchestrator's
    # deterministic summary stays in place otherwise.
    _maybe_llm_explanation(influencer_id, result)
    update_state(campaign_id, phase="score", last_scored_influencer=influencer_id, last_score=result["final_score"])
    # Emit the canonical score.calculated event with the spec's payload
    # shape. The event helper ensures the same field order and rounding
    # regardless of which execution path produced the result.
    event = ScoreCalculated(
        influencer_id=influencer_id,
        overall_fake_risk=float(result.get("overall_fake_risk", 0.0)),
        detection_category=str(result.get("overall_risk_category", "SAFE")),
        risk_category=str(result.get("overall_risk_category", "safe")),
        final_score=float(result.get("final_score", 0.0)),
        grade=str(result.get("grade", "F")),
        confidence=str(result.get("confidence", "Low")),
    ).to_payload()
    emit_event(campaign_id, "score.calculated", event)
    return result
