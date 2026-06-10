from __future__ import annotations

import hashlib

from scoring_service.extraction.handles import normalize_profile_url


def normalized_profile_urls(candidate: dict) -> set[str]:
    values: list[str] = []
    platforms = candidate.get("platforms") or {}
    values.extend(str(value) for value in (platforms.values() if isinstance(platforms, dict) else platforms))
    values.extend(str(value) for value in candidate.get("profile_urls", []) or [])
    if candidate.get("profile_url"):
        values.append(str(candidate["profile_url"]))
    return {normalize_profile_url(value) for value in values if value.startswith("http") or ".com/" in value or "youtu.be/" in value}


def profile_url_hashes(candidate: dict) -> set[str]:
    return {hashlib.sha256(url.encode("utf-8")).hexdigest() for url in normalized_profile_urls(candidate) if url}


def has_exact_profile_match(candidate_a: dict, candidate_b: dict) -> bool:
    return bool(profile_url_hashes(candidate_a) & profile_url_hashes(candidate_b))
