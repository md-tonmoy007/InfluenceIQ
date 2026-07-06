from __future__ import annotations

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

from backend.pipeline.extraction.entities import normalize_name
from backend.pipeline.extraction.handles import username_from_profile
from backend.pipeline.identity.url_match import normalized_profile_urls


def _preferred_name(*candidates: dict) -> str:
    names = [str(candidate.get("canonical_name") or candidate.get("name") or "") for candidate in candidates]
    return max((name for name in names if name), key=lambda name: (not name.startswith("@"), len(name)), default="Unknown creator")


def _unique(values: list) -> list:
    return list(dict.fromkeys(value for value in values if value not in (None, "")))


def _identity_key(candidate: dict, name: str) -> str:
    profile_urls = sorted(normalized_profile_urls(candidate))
    if profile_urls:
        return f"profile:{profile_urls[0]}"

    platform = str(candidate.get("platform") or "").strip().casefold()
    handle = str(candidate.get("handle") or "").strip()
    username = username_from_profile(handle)
    if platform and username:
        return f"handle:{platform}:{username}"

    platforms = dict(candidate.get("platforms") or {})
    for platform_name, value in sorted(platforms.items()):
        username = username_from_profile(str(value))
        if username:
            return f"handle:{str(platform_name).casefold()}:{username}"

    normalized_name = normalize_name(name) or name.strip().casefold()
    return f"name:{normalized_name}"


def canonicalize_candidate(candidate: dict, confidence: float | None = None) -> dict:
    name = _preferred_name(candidate)
    mention = {key: candidate.get(key) for key in ("mention_id", "name", "source_url", "context", "platform") if candidate.get(key) is not None}
    mentions = list(candidate.get("mentions") or []) or ([mention] if mention else [])
    source_urls = _unique([str(item.get("source_url", "")) for item in mentions] + [str(candidate.get("source_url") or "")])
    identity_key = _identity_key(candidate, name)
    return {
        **deepcopy(candidate),
        "influencer_id": str(candidate.get("influencer_id") or uuid5(NAMESPACE_URL, identity_key)),
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
