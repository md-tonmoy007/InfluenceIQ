from __future__ import annotations

import re
from typing import Any

from scoring_service.analysis.bot_behavior import score_bot_behavior
from scoring_service.analysis.brand_safety_blocklist import scan_brand_safety
from scoring_service.analysis.coordinated_engagement import score_coordinated_engagement
from scoring_service.analysis.credibility import calculate_credibility, confidence_for_source_count
from scoring_service.analysis.fake_comment import score_fake_comments
from scoring_service.analysis.fake_follower import score_fake_followers
from scoring_service.analysis.reason_builder import build_reasons, build_summary
from scoring_service.analysis.sentiment import analyze_sentiment
from scoring_service.scoring.normalize import score
from scoring_service.scoring.renormalized_fusion import fuse as fuse_layers
from scoring_service.scoring.risk_components import (
    authentic_engagement_bonus,
    behavioral_signal_score,
    bot_ring_signal_score,
    graph_proxy_score,
    overall_fake_risk,
    overall_risk_category,
    semantic_signal_score,
)
from scoring_service.scoring.role5_fusion import canonical_risk_category
from scoring_service.scoring.trust_formula import calculate_role5_trust
from scoring_service.scoring.versioning import MODEL_VERSION, computed_at


def relevance_score(candidate: dict[str, Any], campaign: dict[str, Any] | None = None) -> float:
    campaign = campaign or {}
    campaign_text = " ".join(str(value) for value in [campaign.get("category", ""), campaign.get("goal", ""), *(campaign.get("interests") or [])])
    candidate_text = " ".join(str(value) for value in [candidate.get("context", ""), candidate.get("bio", ""), *(candidate.get("tags") or [])])
    terms = {term for term in re.findall(r"[a-z0-9]+", campaign_text.casefold()) if len(term) > 2}
    if not terms: return score(candidate.get("relevance_score", candidate.get("relevance", 0)))
    overlap = len(terms & set(re.findall(r"[a-z0-9]+", candidate_text.casefold()))) / len(terms)
    return round(40 + overlap * 60, 2)


def _source_count(candidate: dict[str, Any]) -> int:
    try:
        return max(0, int(candidate.get("data_source_count", len(candidate.get("mentions", []))) or 0))
    except (TypeError, ValueError):
        return 0


def _source_confidence_score(count: int) -> float:
    return 35.0 if count < 3 else 70.0 if count <= 5 else 100.0


def build_role5_scores(candidate: dict[str, Any], campaign: dict[str, Any] | None = None) -> dict[str, Any]:
    comments = candidate.get("comments", []) or []
    comment = score_fake_comments(candidate, comments)
    follower = score_fake_followers(candidate)
    bot = score_bot_behavior(candidate)
    coordinated = score_coordinated_engagement(candidate)
    core = {**comment, **follower, **bot, **coordinated}
    fake_risk = overall_fake_risk(core)
    bonus = authentic_engagement_bonus(candidate)
    engagement_quality = score(100 - fake_risk + bonus)
    sentiment = analyze_sentiment(comments, fake_risk)
    safety_text = " ".join(str(candidate.get(key, "")) for key in ("bio", "content", "context"))
    safety = scan_brand_safety(safety_text, str(candidate.get("source_url", "")))
    source_count = _source_count(candidate)
    authority_value = candidate.get("authority_mentions", [])
    authority_count = len(authority_value) if isinstance(authority_value, list) else int(authority_value or 0)
    credibility = calculate_credibility(
        verified=bool(candidate.get("verified", candidate.get("verified_status", False))),
        professional_titles=candidate.get("professional_titles", []),
        authority_mentions=authority_count,
        credentials=candidate.get("credentials", []), sentiment_score=sentiment["sentiment_score"],
        engagement_quality=engagement_quality, data_source_count=source_count,
        complete_profile=bool(candidate.get("bio_present", candidate.get("bio")) and candidate.get("profile_picture_present", True)),
        fake_comment_risk_score=comment["fake_comment_risk_score"], fake_follower_risk_score=follower["fake_follower_risk_score"],
        bot_behavior_risk_score=bot["bot_behavior_risk_score"], coordinated_engagement_risk_score=coordinated["coordinated_engagement_risk_score"],
        spam_indicators=bool(comment["reasons"]), brand_safety_score=safety["brand_safety_score"])
    relevance = relevance_score(candidate, campaign)
    layer_scores = {
        "semantic": semantic_signal_score(candidate),
        "behavioral": behavioral_signal_score(core, {**candidate, **comment.get("features", {})}),
        "graph_proxy": graph_proxy_score(candidate),
        "bot_rings": bot_ring_signal_score(core, candidate),
        "brand_safety": safety["brand_safety_risk_score"],
    }
    fusion = fuse_layers(layer_scores)
    # The legacy dict-shaped risk score is reconstructed from the
    # dataclass so downstream consumers (and the role-5 tests that
    # assert on it) keep working.
    risk_score = {
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
        "available_layers": list(fusion.available_layers),
        "missing_layers": list(fusion.missing_layers),
        "weight_total": fusion.weight_total,
        "model_version": MODEL_VERSION,
        "model_version_v1_alias": "Role5-FakeSignal-v1",
        "computed_at": computed_at(),
    }
    sub_scores = {
        "relevance_score": relevance, "semantic_signal_score": layer_scores["semantic"],
        "behavioral_signal_score": layer_scores["behavioral"], "graph_proxy_score": layer_scores["graph_proxy"],
        "bot_ring_signal_score": layer_scores["bot_rings"], "fake_comment_risk_score": comment["fake_comment_risk_score"],
        "fake_follower_risk_score": follower["fake_follower_risk_score"], "bot_behavior_risk_score": bot["bot_behavior_risk_score"],
        "coordinated_engagement_risk_score": coordinated["coordinated_engagement_risk_score"],
        "overall_fake_risk_score": fake_risk, "engagement_quality_score": engagement_quality,
        "credibility_score": credibility["credibility_score"], "sentiment_score": sentiment["sentiment_score"],
        "brand_safety_score": safety["brand_safety_score"], "source_confidence_score": _source_confidence_score(source_count),
    }
    severe = any(flag["severity"] == "severe" for flag in safety["flags"])
    trust = calculate_role5_trust(sub_scores, data_source_count=source_count, severe_brand_safety=severe)
    sub_scores.update({"role5_trust_score": trust.role5_trust_score, "role5_fake_risk_score": round(fusion.score * 100, 2)})
    analyses = {"fake_comment": comment, "fake_follower": follower, "bot_behavior": bot,
                "coordinated_engagement": coordinated, "sentiment": sentiment, "brand_safety": safety, "credibility": credibility}
    reasons = build_reasons(analyses)
    category = overall_risk_category(fake_risk)
    score_explanations = {
        "relevance_score": {"reasons": ["Relevance is based on supplied score or campaign term overlap"],
                            "evidence": {"campaign": campaign or {}, "candidate_context": candidate.get("context", "")}},
        "semantic_signal_score": {"reasons": ["Semantic signal aggregates available semantic risk probabilities"] if layer_scores["semantic"] is not None else [],
                                  "evidence": {key: candidate[key] for key in ("spam_probability", "toxicity_probability", "aigc_probability", "claim_mismatch_score", "propaganda_template_match", "repeated_talking_point_score") if candidate.get(key) is not None}},
        "behavioral_signal_score": {"reasons": ["Behavioral signal aggregates available fake-engagement and activity evidence"],
                                    "evidence": {"fake_comment_risk_score": comment["fake_comment_risk_score"], "fake_follower_risk_score": follower["fake_follower_risk_score"], "bot_behavior_risk_score": bot["bot_behavior_risk_score"]}},
        "graph_proxy_score": {"reasons": ["Graph proxy aggregates available local cluster evidence"] if layer_scores["graph_proxy"] is not None else [],
                              "evidence": {key: candidate[key] for key in ("repeated_commenter_cluster_score", "duplicate_text_cluster_score", "suspicious_account_overlap_score", "shared_hashtag_cluster_score", "same_source_cluster_score") if candidate.get(key) is not None}},
        "bot_ring_signal_score": {"reasons": ["Bot-ring signal aggregates coordinated and overlap evidence"],
                                  "evidence": {"coordinated_engagement_risk_score": coordinated["coordinated_engagement_risk_score"], **{key: candidate[key] for key in ("confirmed_bot_overlap_score", "amplifier_account_ratio", "synchronized_activity_score") if candidate.get(key) is not None}}},
        "fake_comment_risk_score": {"reasons": comment["reasons"], "evidence": comment["evidence"]},
        "fake_follower_risk_score": {"reasons": follower["reasons"], "evidence": follower["evidence"]},
        "bot_behavior_risk_score": {"reasons": bot["reasons"], "evidence": bot["evidence"]},
        "coordinated_engagement_risk_score": {"reasons": coordinated["reasons"], "evidence": coordinated["evidence"]},
        "overall_fake_risk_score": {"reasons": list(dict.fromkeys([*comment["reasons"], *follower["reasons"], *bot["reasons"], *coordinated["reasons"]])),
                                    "evidence": {"weighted_components": {key: sub_scores[key] for key in ("fake_comment_risk_score", "fake_follower_risk_score", "bot_behavior_risk_score", "coordinated_engagement_risk_score")}}},
        "engagement_quality_score": {"reasons": ["Engagement quality is reduced by overall fake risk"],
                                     "evidence": {"overall_fake_risk_score": fake_risk, "authentic_engagement_bonus": bonus}},
        "sentiment_score": {"reasons": sentiment["reasons"], "evidence": {"raw_sentiment_score": sentiment["raw_sentiment_score"], "fake_risk_adjustment": sentiment["fake_risk_adjustment"]}},
        "brand_safety_score": {"reasons": safety["reasons"], "evidence": safety["flags"]},
        "credibility_score": {"reasons": credibility["reasons"], "evidence": {"raw_score": credibility["raw_score"], "data_source_count": source_count}},
        "source_confidence_score": {"reasons": [f"Source confidence is {confidence_for_source_count(source_count)} from {source_count} independent sources"],
                                    "evidence": {"data_source_count": source_count}},
        "role5_fake_risk_score": {"reasons": ["Five-layer fake risk uses renormalized available components"],
                                  "evidence": risk_score["components"]},
        "role5_trust_score": {"reasons": list(trust.caps), "evidence": {"positive_trust_score": trust.positive_trust_score, "fake_risk_penalty": trust.fake_risk_penalty}},
    }
    return {"sub_scores": sub_scores, "risk_score": risk_score, "grade": trust.grade,
            "confidence": confidence_for_source_count(source_count), "data_source_count": source_count,
            "positive_reasons": reasons["positive_reasons"], "negative_reasons": reasons["negative_reasons"],
            "reason_evidence": reasons["evidence"], "score_explanations": score_explanations,
            "summary": build_summary(trust.grade, confidence_for_source_count(source_count),
                reasons["positive_reasons"], reasons["negative_reasons"], category),
            "requires_human_review": severe or fake_risk > 65 or safety["requires_llm_review"], "analysis": analyses,
            "overall_risk_category": category, "trust": trust}


def build_influencer_output(candidate: dict[str, Any], campaign: dict[str, Any] | None = None) -> dict[str, Any]:
    result = build_role5_scores(candidate, campaign)
    compact = {"relevance": result["sub_scores"]["relevance_score"], "credibility": result["sub_scores"]["credibility_score"],
        "engagement_quality": result["sub_scores"]["engagement_quality_score"], "sentiment": result["sub_scores"]["sentiment_score"],
        "brand_safety": result["sub_scores"]["brand_safety_score"], "fake_comment_risk": result["sub_scores"]["fake_comment_risk_score"],
        "fake_follower_risk": result["sub_scores"]["fake_follower_risk_score"], "bot_behavior_risk": result["sub_scores"]["bot_behavior_risk_score"],
        "coordinated_engagement_risk": result["sub_scores"]["coordinated_engagement_risk_score"],
        "overall_fake_risk": result["sub_scores"]["overall_fake_risk_score"], "role5_trust_score": result["sub_scores"]["role5_trust_score"]}
    return {"influencer_id": str(candidate.get("influencer_id", "")), "canonical_name": candidate.get("canonical_name", candidate.get("name", "")),
        "platforms": candidate.get("platforms", {}), "profile_urls": candidate.get("profile_urls", []), "credentials": candidate.get("credentials", []),
        "professional_titles": candidate.get("professional_titles", []), "mentions": candidate.get("mentions", []), "sub_scores": compact,
        "signal_scores": result["sub_scores"], "risk_score": result["risk_score"], "grade": result["grade"], "confidence": result["confidence"],
        "data_source_count": result["data_source_count"], "positive_reasons": result["positive_reasons"], "negative_reasons": result["negative_reasons"],
        "reason_evidence": result["reason_evidence"], "score_explanations": result["score_explanations"],
        "explanation": result["summary"], "source_urls": candidate.get("source_urls", [candidate["source_url"]] if candidate.get("source_url") else []),
        "requires_human_review": result["requires_human_review"]}


def build_sub_scores(candidate: dict[str, Any], campaign: dict[str, Any] | None = None) -> dict[str, Any]:
    """Legacy five-score view retained for existing Role 1/3 consumers."""
    result = build_role5_scores(candidate, campaign)
    full = result["sub_scores"]
    return {"sub_scores": {"relevance": full["relevance_score"], "credibility": full["credibility_score"],
            "engagement": full["engagement_quality_score"], "sentiment": full["sentiment_score"],
            "brand_safety": full["brand_safety_score"], "data_source_count": result["data_source_count"]},
            "analysis": {**result["analysis"], "role5": result}}
