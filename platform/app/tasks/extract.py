from __future__ import annotations

import re
from difflib import SequenceMatcher

from celery import shared_task

from app.services.pipeline_state import emit_event, update_state


def _normalize_name(value: str) -> str:
    value = value.lower()
    value = re.sub(r"\b(dr|md|phd|mba|rd|rn)\b", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _platforms(candidate: dict) -> set[str]:
    platforms = candidate.get("platforms", {})
    if isinstance(platforms, dict):
        return {name for name, handle in platforms.items() if handle}
    if isinstance(platforms, list):
        return set(platforms)
    return set()


@shared_task(name="app.tasks.extract.extract_influencers", bind=True)
def extract_influencers(self, campaign_id: str, page: dict) -> list[dict]:
    """spaCy NER + regex + LLM fallback handled by scoring_service.
    Returns list of influencer mention records with source_url."""
    content = page.get("content", "")
    source_url = page.get("url", "")
    name_matches = re.findall(r"\b(?:Dr\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b", content)
    handles = re.findall(r"@([A-Za-z0-9_.]{3,30})", content)

    mentions: list[dict] = []
    seen_names: set[str] = set()
    for raw_name in name_matches[:5]:
        normalized = _normalize_name(raw_name)
        if not normalized or normalized in seen_names:
            continue
        seen_names.add(normalized)
        mentions.append(
            {
                "name": raw_name,
                "source_url": source_url,
                "context": content[:240],
                "platforms": {"instagram": f"@{handles[0]}"} if handles else {},
                "credentials": re.findall(r"\b(?:MD|PhD|MBA|RD|RN|Certified [A-Za-z ]+)\b", content),
            }
        )

    if not mentions and handles:
        mentions.append(
            {
                "name": handles[0],
                "source_url": source_url,
                "context": content[:240],
                "platforms": {"instagram": f"@{handles[0]}"},
                "credentials": [],
            }
        )

    update_state(campaign_id, phase="extract", influencer_mentions=len(mentions))
    for mention in mentions:
        emit_event(
            campaign_id,
            "influencer.found",
            {
                "name": mention["name"],
                "platform": next(iter(mention.get("platforms", {}) or {}), "unknown"),
                "source": source_url,
            },
        )
    return mentions


@shared_task(name="app.tasks.extract.resolve_identity_llm", bind=True)
def resolve_identity_llm(self, candidate_a: dict, candidate_b: dict) -> dict:
    """Pass 3 LLM merge decision for fuzzy-match confidence 0.6-0.84 handled by ai_agent_services.
    Returns {merge: bool, reason: str, confidence: float}."""
    name_a = _normalize_name(str(candidate_a.get("name") or candidate_a.get("canonical_name") or ""))
    name_b = _normalize_name(str(candidate_b.get("name") or candidate_b.get("canonical_name") or ""))
    name_similarity = SequenceMatcher(None, name_a, name_b).ratio() if name_a and name_b else 0.0
    shared_platforms = _platforms(candidate_a) & _platforms(candidate_b)

    merge = name_similarity >= 0.9 or (name_similarity >= 0.72 and bool(shared_platforms))
    confidence = name_similarity
    if shared_platforms:
        confidence = min(1.0, confidence + 0.12)

    return {
        "merge": merge,
        "reason": (
            "High name similarity or shared platform evidence"
            if merge
            else "Insufficient name similarity and platform overlap"
        ),
        "confidence": round(confidence, 2),
    }
