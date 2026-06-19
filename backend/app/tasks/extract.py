from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(name="app.tasks.extract.extract_influencers", bind=True)
def extract_influencers(self, campaign_id: str, page: dict) -> list[dict]:
    """spaCy NER + regex + LLM fallback. Owner: Scoring.
    Returns list of influencer mention records with source_url."""
    raise NotImplementedError("Day 2 task (Scoring)")


@celery_app.task(name="app.tasks.extract.resolve_identity_llm", bind=True)
def resolve_identity_llm(self, candidate_a: dict, candidate_b: dict) -> dict:
    """Pass 3 LLM merge decision for fuzzy-match confidence 0.6–0.84. Owner: AI/DevOps.
    Returns {merge: bool, reason: str, confidence: float}."""
    raise NotImplementedError("Day 3 task")
