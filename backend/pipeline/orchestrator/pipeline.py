"""End-to-end Role 4 pipeline orchestrator.

This module is the single public entry point for role-4
(Pipeline Intelligence). It composes:

* :mod:`backend.pipeline.detection`        - 5 fake-risk detectors + classifier
* :mod:`backend.pipeline.analysis`         - sentiment, engagement, credibility
* :mod:`backend.pipeline.fusion`          - 5-layer fusion + trust formula

The orchestrator is intentionally synchronous, deterministic, and
free of I/O. It returns a fully-formed :class:`Role4PipelineResult`
that matches the backend/frontend contract documented in
:doc:`/docs/Role-4-Pipeline-Intelligence.md`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from backend.pipeline.analysis.bot_behavior import score_bot_behavior
from backend.pipeline.analysis.brand_safety_blocklist import scan_brand_safety
from backend.pipeline.analysis.coordinated_engagement import score_coordinated_engagement
from backend.pipeline.analysis.credibility import calculate_credibility
from backend.pipeline.analysis.engagement_quality import engagement_quality_score
from backend.pipeline.analysis.fake_comment import score_fake_comments
from backend.pipeline.analysis.fake_follower import score_fake_followers
from backend.pipeline.analysis.reason_builder import build_reasons, build_summary
from backend.pipeline.analysis.sentiment import analyze_sentiment
from backend.pipeline.analysis.source_confidence import source_confidence_score
from backend.pipeline.detection import (
    DetectionDecision,
    classify_detection,
    detect_bot_behavior,
    detect_brand_safety,
    detect_coordinated_engagement,
    detect_fake_comments,
    detect_fake_followers,
)
from backend.pipeline.events import ScoreCalculated
from backend.pipeline.extraction.contact_info import (
    CONTACT_INFO_ENABLED,
    ContactInfo,
    merge_contact_info,
)
from backend.pipeline.fusion.components import (
    behavioral_signal_score_with_provenance,
    bot_ring_signal_score,
    graph_proxy_score,
    overall_fake_risk,
    overall_risk_category,
    semantic_signal_score_with_provenance,
)
from backend.pipeline.fusion.fusion import fuse as fuse_layers
from backend.pipeline.fusion.legacy import canonical_risk_category
from backend.pipeline.fusion.sub_scores import relevance_score
from backend.pipeline.fusion.trust import calculate_role4_trust
from backend.pipeline.fusion.versioning import computed_at, model_version_for


def _source_count(candidate: dict[str, Any]) -> int:
    """Derive the source count from the candidate."""
    raw = candidate.get("data_source_count", len(candidate.get("mentions", [])) or 0)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _brand_safety_text(candidate: dict[str, Any]) -> str:
    return " ".join(str(candidate.get(key, "")) for key in ("bio", "content", "context"))


def _flatten_evidence(*blocks: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for block in blocks:
        if not block:
            continue
        for key, value in block.items():
            if value is not None and value != {} and value != []:
                out[key] = value
    return out


def _collect_contact_info(candidate: dict[str, Any]) -> ContactInfo:
    """Union every contact list across the candidate's mentions and the
    candidate's own contact fields.

    The candidate can carry a top-level ``contact_info`` dict (the
    raw extractor's output) or each mention can carry its own
    ``emails`` / ``phones`` / ``websites`` / ``addresses`` list (the
    per-mention contact_info populated by
    :func:`extract_influencer_mentions`).

    Returns a disabled :class:`ContactInfo` when the global
    :data:`CONTACT_INFO_ENABLED` flag is false. The orchestrator then
    omits the public ``contact_info`` block from the score event
    entirely.
    """
    if not CONTACT_INFO_ENABLED:
        return ContactInfo(enabled=False)
    bundles: list[ContactInfo | dict[str, Any] | None] = []
    if isinstance(candidate.get("contact_info"), dict):
        bundles.append(candidate["contact_info"])
    for mention in candidate.get("mentions", []) or []:
        if not isinstance(mention, dict):
            continue
        if any(mention.get(key) for key in ("emails", "phones", "websites", "addresses")):
            bundles.append({
                "emails": mention.get("emails", []),
                "phones": mention.get("phones", []),
                "websites": mention.get("websites", []),
                "addresses": mention.get("addresses", []),
                "enabled": mention.get("contact_info_enabled", True),
            })
    return merge_contact_info(bundles)


@dataclass
class Role4PipelineResult:
    """Result of :func:`run_role4_pipeline`.

    The dataclass exposes the full role-4 output contract:

    * ``detection``         - DetectionCategory + per-detector booleans
    * ``sub_scores``        - Compact 0-100 sub-scores for the dashboard
    * ``signal_scores``     - Full signal-score-ready values (signal_scores
                              table contract from the previous project)
    * ``risk_score``        - UMGL-compatible risk JSON
    * ``grade``/``confidence``/``data_source_count`` - aggregate metadata
    * ``positive_reasons``/``negative_reasons`` - explainability
    * ``contact_info``      - Union of all mention-level contact lists
                              (PII - backend-only, not for events)
    * ``score_event``       - pre-built score.calculated event payload
                              with **redacted** contact_info
    """

    influencer_id: str
    canonical_name: str
    platforms: dict[str, str]
    profile_urls: list[str]
    credentials: list[str]
    professional_titles: list[str]
    mentions: list[dict[str, Any]]
    detection: dict[str, Any]
    sub_scores: dict[str, float]
    signal_scores: dict[str, float | None]
    risk_score: dict[str, Any]
    grade: str
    confidence: str
    data_source_count: int
    positive_reasons: list[str]
    negative_reasons: list[str]
    source_urls: list[str]
    requires_human_review: bool
    explanation: str
    contact_info: dict[str, Any] = field(default_factory=dict)
    score_event: dict[str, Any] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)
    score_explanations: dict[str, Any] = field(default_factory=dict)
    signal_model_versions: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_role4_pipeline(candidate: dict[str, Any],
                       campaign: dict[str, Any] | None = None) -> Role4PipelineResult:
    """Run the full role-4 pipeline on a single candidate."""
    comments = candidate.get("comments", []) or []

    # ---- Pipeline 4-7: per-detector fake-risk scorers ----
    comment_result = score_fake_comments(candidate, comments)
    follower_result = score_fake_followers(candidate)
    bot_result = score_bot_behavior(candidate)
    coordinated_result = score_coordinated_engagement(candidate)

    fake_comment_score = float(comment_result["fake_comment_risk_score"])
    fake_follower_score = float(follower_result["fake_follower_risk_score"])
    bot_score = float(bot_result["bot_behavior_risk_score"])
    coordinated_score = float(coordinated_result["coordinated_engagement_risk_score"])

    core = {
        "fake_comment_risk_score": fake_comment_score,
        "fake_follower_risk_score": fake_follower_score,
        "bot_behavior_risk_score": bot_score,
        "coordinated_engagement_risk_score": coordinated_score,
    }
    overall_fake = overall_fake_risk(core)

    # ---- Detection (Pipeline 3) ----
    safety_text = _brand_safety_text(candidate)
    safety_scan = scan_brand_safety(safety_text, str(candidate.get("source_url", "")))
    safety = detect_brand_safety(safety_text, str(candidate.get("source_url", "")))
    bot_detection = detect_bot_behavior(candidate)
    follower_detection = detect_fake_followers(candidate)
    comment_detection = detect_fake_comments(features=candidate, comments=comments)
    coordinated_detection = detect_coordinated_engagement(candidate)

    source_count = _source_count(candidate)
    decision: DetectionDecision = classify_detection(
        overall_fake_risk_score=overall_fake,
        bot_behavior_risk_score=bot_score,
        fake_follower_risk_score=fake_follower_score,
        fake_comment_risk_score=fake_comment_score,
        coordinated_engagement_risk_score=coordinated_score,
        brand_safety_score=safety["score"],
        data_source_count=source_count,
        brand_safety_requires_llm=safety["requires_llm_review"],
    )

    # ---- Sub-scores (Pipelines 11-15) ----
    engagement = engagement_quality_score(overall_fake, candidate)
    sentiment = analyze_sentiment(comments, overall_fake)
    source_conf = source_confidence_score(candidate.get("source_evidence") or {
        "data_source_count": source_count,
        "verified_source_count": candidate.get("verified_source_count", 0),
        "profile_url_available": bool(candidate.get("profile_urls") or candidate.get("profile_url")),
        "metadata_completeness": candidate.get("metadata_completeness", 0.0),
        "same_source_repetition": candidate.get("same_source_repetition", 0.0),
    })
    relevance = relevance_score(candidate, campaign)

    authority_value = candidate.get("authority_mentions", [])
    authority_count = len(authority_value) if isinstance(authority_value, list) else int(authority_value or 0)
    credibility = calculate_credibility(
        verified=bool(candidate.get("verified", candidate.get("verified_status", False))),
        professional_titles=candidate.get("professional_titles", []),
        authority_mentions=authority_count,
        credentials=candidate.get("credentials", []),
        sentiment_score=float(sentiment["sentiment_score"]),
        engagement_quality=float(engagement["engagement_quality_score"]),
        data_source_count=source_count,
        complete_profile=bool(candidate.get("bio_present", candidate.get("bio"))
                              and candidate.get("profile_picture_present", True)),
        fake_comment_risk_score=fake_comment_score,
        fake_follower_risk_score=fake_follower_score,
        bot_behavior_risk_score=bot_score,
        coordinated_engagement_risk_score=coordinated_score,
        spam_indicators=bool(comment_result["reasons"]),
        brand_safety_score=safety["score"],
    )

    # ---- Five-layer ensemble (Pipeline 9) ----
    # The semantic and behavioral layers run through their v2-aware
    # variants so we can record whether a backend.ml adapter fired and
    # surface the model provenance. Graph and bot-rings v2 are inert
    # in v1 — see :mod:`backend.pipeline.fusion.backends.ml_adapters`.
    semantic_score, semantic_v2_used, semantic_versions = semantic_signal_score_with_provenance(candidate)
    behavioral_score, behavioral_v2_used, behavioral_versions = behavioral_signal_score_with_provenance(
        core, {**candidate, **comment_result.get("features", {})},
    )
    layer_scores: dict[str, float | None] = {
        "semantic": semantic_score,
        "behavioral": behavioral_score,
        "graph_proxy": graph_proxy_score(candidate),
        "bot_rings": bot_ring_signal_score(core, candidate),
        "brand_safety": float(safety["risk_score"]),
    }
    fusion = fuse_layers(layer_scores)
    risk_category_band = overall_risk_category(overall_fake)

    # Per-layer model provenance. Always a dict (never None) so
    # downstream consumers can iterate without a None check.
    signal_model_versions: dict[str, dict[str, str]] = {}
    if semantic_v2_used and semantic_versions:
        signal_model_versions["semantic"] = semantic_versions
    if behavioral_v2_used and behavioral_versions:
        signal_model_versions["behavioral"] = behavioral_versions

    # ---- Sub-score aggregation for the frontend ----
    sub_scores = {
        "relevance": round(float(relevance), 2),
        "credibility": round(float(credibility["credibility_score"]), 2),
        "engagement_quality": round(float(engagement["engagement_quality_score"]), 2),
        "sentiment": round(float(sentiment["sentiment_score"]), 2),
        "brand_safety": round(float(safety["score"]), 2),
        "source_confidence": round(float(source_conf["source_confidence_score"]), 2),
        "fake_comment_risk": round(fake_comment_score, 2),
        "fake_follower_risk": round(fake_follower_score, 2),
        "bot_behavior_risk": round(bot_score, 2),
        "coordinated_engagement_risk": round(coordinated_score, 2),
        "overall_fake_risk": round(overall_fake, 2),
        "role4_trust_score": 0.0,  # filled below
    }

    severe_brand_safety = any(flag.get("severity") == "severe" for flag in safety_scan.get("flags", []))
    trust_input = {
        "relevance_score": sub_scores["relevance"],
        "credibility_score": sub_scores["credibility"],
        "engagement_quality_score": sub_scores["engagement_quality"],
        "sentiment_score": sub_scores["sentiment"],
        "brand_safety_score": sub_scores["brand_safety"],
        "source_confidence_score": sub_scores["source_confidence"],
        "overall_fake_risk_score": overall_fake,
    }
    trust = calculate_role4_trust(
        trust_input,
        data_source_count=source_count,
        severe_brand_safety=severe_brand_safety,
        positive_weights=campaign.get("positive_weights") if campaign else None,
    )
    sub_scores["role4_trust_score"] = trust.role4_trust_score

    # ---- Signal scores (Pipeline 6 - signal_scores table contract) ----
    signal_scores: dict[str, float | None] = {
        "fake_comment_risk_score": fake_comment_score,
        "fake_follower_risk_score": fake_follower_score,
        "bot_behavior_risk_score": bot_score,
        "coordinated_engagement_risk_score": coordinated_score,
        "overall_fake_risk_score": overall_fake,
        "credibility_score": float(credibility["credibility_score"]),
        "sentiment_score": float(sentiment["sentiment_score"]),
        "brand_safety_score": float(safety["score"]),
        "engagement_quality_score": float(engagement["engagement_quality_score"]),
        "source_confidence_score": float(source_conf["source_confidence_score"]),
        "semantic_signal_score": layer_scores["semantic"],
        "behavioral_signal_score": layer_scores["behavioral"],
        "graph_proxy_score": layer_scores["graph_proxy"],
        "bot_ring_signal_score": layer_scores["bot_rings"],
    }

    risk_score_payload = {
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
        "model_version": model_version_for(
            semantic_v2=semantic_v2_used,
            behavioral_v2=behavioral_v2_used,
            graph_v2=False,    # inert in v1
            bot_rings_v2=False,  # inert in v1
        ),
        "computed_at": computed_at(),
    }

    # ---- Reasons and summary (Pipeline 18) ----
    analyses = {
        "fake_comment": comment_result,
        "fake_follower": follower_result,
        "bot_behavior": bot_result,
        "coordinated_engagement": coordinated_result,
        "sentiment": sentiment,
        "brand_safety": safety_scan,
        "credibility": credibility,
        "engagement_quality": engagement,
        "source_confidence": source_conf,
        "detection": decision.as_dict(),
    }
    reasons = build_reasons(analyses)
    summary = build_summary(trust.grade, trust_grade_to_confidence(source_count, trust.grade, sub_scores),
                            reasons["positive_reasons"], reasons["negative_reasons"], decision.category.value)

    # ---- Score.calculated event payload (Pipeline 19) ----
    # The event payload is **always redacted** for PII: emails / phones
    # / websites / addresses are SHA-256 truncated before serialisation
    # so the public WebSocket stream never carries raw PII. The full
    # plain-text values stay on :attr:`contact_info` for the backend to
    # persist in PostgreSQL.
    contact_info = _collect_contact_info(candidate)
    score_event = ScoreCalculated(
        influencer_id=str(candidate.get("influencer_id", "")),
        overall_fake_risk=overall_fake,
        detection_category=decision.category.value,
        risk_category=canonical_risk_category(fusion.score),
        final_score=trust.role4_trust_score,
        grade=trust.grade,
        confidence=trust_grade_to_confidence(source_count, trust.grade, sub_scores),
        contact_info=contact_info.to_dict() if contact_info.enabled else None,
    ).to_payload()

    # ---- Source URLs ----
    source_urls = list(dict.fromkeys(
        [*(str(url) for url in candidate.get("source_urls", []) or []),
         str(candidate.get("source_url") or ""),
         *[str(m.get("source_url", "")) for m in candidate.get("mentions", []) if m.get("source_url")]],
    ) if candidate.get("mentions") else list(dict.fromkeys(
        [*(str(url) for url in candidate.get("source_urls", []) or []),
         str(candidate.get("source_url") or "")],
    )))
    source_urls = [u for u in source_urls if u]

    score_explanations = {
        "relevance_score": {"value": sub_scores["relevance"], "reason": "Relevance is based on supplied score or campaign term overlap"},
        "fake_comment_risk_score": {"value": fake_comment_score, "reasons": comment_result["reasons"], "evidence": comment_result["evidence"]},
        "fake_follower_risk_score": {"value": fake_follower_score, "reasons": follower_result["reasons"], "evidence": follower_result["evidence"]},
        "bot_behavior_risk_score": {"value": bot_score, "reasons": bot_result["reasons"], "evidence": bot_result["evidence"]},
        "coordinated_engagement_risk_score": {"value": coordinated_score, "reasons": coordinated_result["reasons"], "evidence": coordinated_result["evidence"]},
        "overall_fake_risk_score": {"value": overall_fake, "components": core, "category": risk_category_band},
        "engagement_quality_score": {"value": sub_scores["engagement_quality"], "evidence": engagement["evidence"]},
        "sentiment_score": {"value": sub_scores["sentiment"], "raw": sentiment["raw_sentiment_score"], "adjustment": sentiment["fake_risk_adjustment"]},
        "brand_safety_score": {"value": sub_scores["brand_safety"], "flags": safety_scan.get("flags", []), "requires_llm_review": safety_scan.get("requires_llm_review")},
        "credibility_score": {"value": sub_scores["credibility"], "raw_score": credibility["raw_score"], "confidence_capped": credibility["confidence_capped"]},
        "source_confidence_score": {"value": sub_scores["source_confidence"], "components": source_conf["components"]},
        "role4_trust_score": {"value": trust.role4_trust_score, "grade": trust.grade, "positive": trust.positive_trust_score, "penalty": trust.fake_risk_penalty, "caps": trust.caps},
    }

    return Role4PipelineResult(
        influencer_id=str(candidate.get("influencer_id", "")),
        canonical_name=str(candidate.get("canonical_name") or candidate.get("name", "")),
        platforms=candidate.get("platforms", {}) or {},
        profile_urls=list(candidate.get("profile_urls", []) or []),
        credentials=list(candidate.get("credentials", []) or []),
        professional_titles=list(candidate.get("professional_titles", []) or []),
        mentions=list(candidate.get("mentions", []) or []),
        detection=decision.as_dict(),
        sub_scores=sub_scores,
        signal_scores=signal_scores,
        risk_score=risk_score_payload,
        grade=trust.grade,
        confidence=trust_grade_to_confidence(source_count, trust.grade, sub_scores),
        data_source_count=source_count,
        positive_reasons=reasons["positive_reasons"],
        negative_reasons=reasons["negative_reasons"],
        source_urls=source_urls,
        requires_human_review=decision.requires_human_review,
        explanation=summary,
        contact_info=contact_info.to_dict() if contact_info.enabled else {
            "emails": [], "phones": [], "websites": [], "addresses": [], "enabled": False,
        },
        score_event=score_event,
        analysis=analyses,
        score_explanations=score_explanations,
        signal_model_versions=signal_model_versions,
    )


def trust_grade_to_confidence(source_count: int, grade: str, sub_scores: dict[str, float]) -> str:
    if source_count < 3:
        return "Low"
    if source_count <= 5:
        return "Medium"
    return "High"


__all__ = [
    "Role4PipelineResult",
    "run_role4_pipeline",
    "trust_grade_to_confidence",
]
