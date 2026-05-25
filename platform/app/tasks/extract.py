from __future__ import annotations

from celery import shared_task


@shared_task(name="app.tasks.extract.extract_influencers", bind=True)
def extract_influencers(self, campaign_id: str, page: dict) -> list[dict]:
    """spaCy NER + regex + LLM fallback handled by scoring_service.
    Returns list of influencer mention records with source_url."""
    raise NotImplementedError("Day 2 task (Scoring)")


@shared_task(name="app.tasks.extract.resolve_identity_llm", bind=True)
def resolve_identity_llm(self, candidate_a: dict, candidate_b: dict) -> dict:
    """Pass 3 LLM merge decision for fuzzy-match confidence 0.6-0.84 handled by ai_agent_services.
    Returns {merge: bool, reason: str, confidence: float}."""
    raise NotImplementedError("Day 3 task")
