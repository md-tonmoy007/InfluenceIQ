from __future__ import annotations

from celery import shared_task

from app.services.pipeline_state import emit_event, update_state
from scoring_service.extraction.entities import extract_influencer_mentions
from scoring_service.identity.resolver import resolve_candidates


@shared_task(name="app.tasks.extract.extract_influencers", bind=True)
def extract_influencers(self, campaign_id: str, page: dict) -> list[dict]:
    """Deterministic extraction with optional spaCy PERSON enrichment.
    Returns list of influencer mention records with source_url."""
    mentions = extract_influencer_mentions(page)
    source_url = str(page.get("url") or page.get("source_url") or "")

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
    """Three-pass identity decision with a deterministic Pass 3 fallback.
    Returns {merge: bool, reason: str, confidence: float}."""
    decision = resolve_candidates(candidate_a, candidate_b)
    return {
        "merge": decision["merge"],
        "reason": decision["reason"],
        "confidence": round(float(decision["confidence"]), 2),
        "strategy": decision["strategy"],
        "requires_llm": decision["requires_llm"],
    }
