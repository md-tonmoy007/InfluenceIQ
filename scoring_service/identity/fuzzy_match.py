from __future__ import annotations

from difflib import SequenceMatcher

from scoring_service.extraction.entities import normalize_name
from scoring_service.extraction.handles import username_stems


def _ratio(value_a: str, value_b: str) -> float:
    if not value_a or not value_b:
        return 0.0
    try:
        from rapidfuzz.fuzz import ratio
        return ratio(value_a, value_b) / 100.0
    except ImportError:
        return SequenceMatcher(None, value_a, value_b).ratio()


def _evidence_similarity(candidate_a: dict, candidate_b: dict) -> float:
    evidence_a = {str(v).casefold() for key in ("credentials", "professional_titles") for v in candidate_a.get(key, []) or []}
    evidence_b = {str(v).casefold() for key in ("credentials", "professional_titles") for v in candidate_b.get(key, []) or []}
    return len(evidence_a & evidence_b) / len(evidence_a | evidence_b) if evidence_a | evidence_b else 0.0


def candidate_similarity(candidate_a: dict, candidate_b: dict) -> dict[str, float | bool]:
    name_a = normalize_name(str(candidate_a.get("name") or candidate_a.get("canonical_name") or ""))
    name_b = normalize_name(str(candidate_b.get("name") or candidate_b.get("canonical_name") or ""))
    name_score = _ratio(name_a, name_b)
    usernames_a, usernames_b = username_stems(candidate_a), username_stems(candidate_b)
    username_score = max((_ratio(a, b) for a in usernames_a for b in usernames_b), default=0.0)
    evidence_score = _evidence_similarity(candidate_a, candidate_b)
    platforms_a = set((candidate_a.get("platforms") or {}).keys())
    platforms_b = set((candidate_b.get("platforms") or {}).keys())
    platform_overlap = bool(platforms_a & platforms_b)
    confidence = max(username_score, name_score * 0.75 + max(evidence_score, float(platform_overlap)) * 0.25)
    if usernames_a & usernames_b:
        confidence = max(confidence, 0.98)
    return {"name_similarity": round(name_score, 4), "username_similarity": round(username_score, 4),
            "evidence_similarity": round(evidence_score, 4), "platform_overlap": platform_overlap,
            "confidence": round(min(1.0, confidence), 4)}
