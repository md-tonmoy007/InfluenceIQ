from __future__ import annotations

import math
import re
from typing import Any

_NEUTRAL_RELEVANCE_SCORE = 50.0


def relevance_score(candidate: dict[str, Any], campaign: dict[str, Any] | None = None) -> float:
    """Score 0-100 for campaign-to-candidate relevance.

    Uses cosine similarity over pre-computed OpenRouter embeddings when
    both sides carry a ``"source":"openrouter"`` envelope.  Falls back
    to token-overlap relevance otherwise (no key, stub, or embedding
    unavailable).
    """
    candidate_emb = (candidate.get("embedding") or {}) if isinstance(candidate.get("embedding"), dict) else {}
    campaign_emb = (campaign or {}).get("embedding") or {}
    if not isinstance(campaign_emb, dict):
        campaign_emb = {}

    if candidate_emb.get("source") == "openrouter" and campaign_emb.get("source") == "openrouter":
        c_vec = candidate_emb.get("vector") or []
        p_vec = campaign_emb.get("vector") or []
        if c_vec and p_vec and len(c_vec) == len(p_vec):
            similarity = _cosine_similarity(c_vec, p_vec)
            if similarity is not None:
                return round(similarity * 100.0, 2)

    return _token_overlap_relevance(candidate, campaign or {})


def _token_overlap_relevance(candidate: dict[str, Any], campaign: dict[str, Any]) -> float:
    campaign_text = " ".join(
        str(value)
        for value in [
            campaign.get("description", ""),
            campaign.get("niche", ""),
            campaign.get("target_audience", ""),
            campaign.get("goals", ""),
            campaign.get("product", ""),
            *(campaign.get("locations") or []),
        ]
    )
    candidate_text = " ".join(
        str(value)
        for value in [
            candidate.get("context", ""),
            candidate.get("bio", ""),
            *(candidate.get("tags") or []),
        ]
    )
    terms = {term for term in re.findall(r"[a-z0-9]+", campaign_text.casefold()) if len(term) > 2}
    if not terms:
        return _NEUTRAL_RELEVANCE_SCORE
    overlap = len(terms & set(re.findall(r"[a-z0-9]+", candidate_text.casefold()))) / len(terms)
    return round(40 + overlap * 60, 2)


def _cosine_similarity(a: list[float], b: list[float]) -> float | None:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return None
    return dot / (norm_a * norm_b)
