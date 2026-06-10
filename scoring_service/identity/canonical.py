from __future__ import annotations

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

from scoring_service.extraction.entities import normalize_name
from scoring_service.identity.url_match import normalized_profile_urls


def _preferred_name(*candidates: dict) -> str:
    names = [str(candidate.get("canonical_name") or candidate.get("name") or "") for candidate in candidates]
    return max((name for name in names if name), key=lambda name: (not name.startswith("@"), len(name)), default="Unknown creator")


def _unique(values: list) -> list:
    return list(dict.fromkeys(value for value in values if value not in (None, "")))


def canonicalize_candidate(candidate: dict, confidence: float | None = None) -> dict:
    name = _preferred_name(candidate)
    mention = {key: candidate.get(key) for key in ("mention_id", "name", "source_url", "context", "platform") if candidate.get(key) is not None}
    mentions = list(candidate.get("mentions") or []) or ([mention] if mention else [])
    source_urls = _unique([str(item.get("source_url", "")) for item in mentions] + [str(candidate.get("source_url") or "")])
    return {
        **deepcopy(candidate),
        "influencer_id": str(candidate.get("influencer_id") or uuid5(NAMESPACE_URL, normalize_name(name) or name)),
        "canonical_name": name,
        "platforms": dict(candidate.get("platforms") or {}),
        "profile_urls": sorted(normalized_profile_urls(candidate)),
        "credentials": _unique(list(candidate.get("credentials") or [])),
        "professional_titles": _unique(list(candidate.get("professional_titles") or [])),
        "mentions": mentions,
        "identity_confidence": round(float(confidence if confidence is not None else candidate.get("identity_confidence", 1.0)), 4),
        "data_source_count": len(source_urls),
        "source_urls": source_urls,
    }


def merge_candidates(candidate_a: dict, candidate_b: dict, confidence: float = 1.0) -> dict:
    a, b = canonicalize_candidate(candidate_a), canonicalize_candidate(candidate_b)
    platforms = {**b["platforms"], **a["platforms"]}
    mentions, seen = [], set()
    for mention in [*a["mentions"], *b["mentions"]]:
        key = (str(mention.get("mention_id", "")), str(mention.get("name", "")).casefold(), str(mention.get("source_url", "")))
        if key not in seen:
            seen.add(key)
            mentions.append(mention)
    merged = {
        **a, "canonical_name": _preferred_name(candidate_a, candidate_b), "platforms": platforms,
        "profile_urls": _unique([*a["profile_urls"], *b["profile_urls"]]),
        "credentials": _unique([*a["credentials"], *b["credentials"]]),
        "professional_titles": _unique([*a["professional_titles"], *b["professional_titles"]]),
        "mentions": mentions, "identity_confidence": round(confidence, 4),
    }
    source_urls = _unique([str(item.get("source_url", "")) for item in mentions])
    merged["source_urls"] = source_urls
    merged["data_source_count"] = len(source_urls)
    return merged
