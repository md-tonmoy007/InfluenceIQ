from __future__ import annotations

from collections.abc import Callable

from backend.pipeline.identity.canonical import canonicalize_candidate, merge_candidates
from backend.pipeline.identity.fuzzy_match import candidate_similarity
from backend.pipeline.identity.url_match import has_exact_profile_match


def resolve_candidates(candidate_a: dict, candidate_b: dict) -> dict:
    if has_exact_profile_match(candidate_a, candidate_b):
        return {"merge": True, "reason": "Exact normalized social profile URL match", "confidence": 1.0,
                "strategy": "profile_url", "requires_llm": False,
                "canonical": merge_candidates(candidate_a, candidate_b, 1.0)}

    similarity = candidate_similarity(candidate_a, candidate_b)
    name_score = float(similarity["name_similarity"])
    username_score = float(similarity["username_similarity"])
    evidence_score = float(similarity["evidence_similarity"])
    platform_overlap = bool(similarity["platform_overlap"])
    merge = username_score >= 0.90 or (name_score >= 0.85 and (platform_overlap or evidence_score > 0))
    confidence = max(float(similarity["confidence"]), 0.85 if merge else 0.0)
    requires_llm = not merge and 0.60 <= confidence <= 0.84
    reason = "Fuzzy name/username and supporting evidence match" if merge else (
        "Ambiguous fuzzy match requires Role 1 LLM resolution" if requires_llm else "Identity evidence does not support a merge")
    return {"merge": merge, "reason": reason, "confidence": round(confidence, 4), "strategy": "fuzzy",
            "requires_llm": requires_llm, "similarity": similarity,
            "canonical": merge_candidates(candidate_a, candidate_b, confidence) if merge else None}


def resolve_identity_clusters(
    candidates: list[dict], *, campaign_id: str | None = None,
    event_emitter: Callable[[str, str, dict], object] | None = None,
) -> dict[str, list]:
    canonical: list[dict] = []
    ambiguous_pairs: list[dict] = []
    merge_events: list[dict] = []
    for candidate in candidates:
        merged = False
        for index, existing in enumerate(canonical):
            decision = resolve_candidates(existing, candidate)
            if decision["merge"]:
                before = [str(m.get("mention_id")) for m in existing.get("mentions", []) if m.get("mention_id")]
                if candidate.get("mention_id"):
                    before.append(str(candidate["mention_id"]))
                canonical[index] = decision["canonical"]
                payload = {"canonical_id": canonical[index]["influencer_id"], "merged_from": list(dict.fromkeys(before)),
                           "confidence": decision["confidence"]}
                merge_events.append(payload)
                if event_emitter and campaign_id:
                    event_emitter(campaign_id, "identity.merged", payload)
                merged = True
                break
            if decision["requires_llm"]:
                ambiguous_pairs.append({"candidate_a": existing, "candidate_b": candidate,
                                        "confidence": decision["confidence"], "reason": decision["reason"]})
        if not merged:
            canonical.append(canonicalize_candidate(candidate))
    return {"canonical": canonical, "ambiguous_pairs": ambiguous_pairs, "merge_events": merge_events}
