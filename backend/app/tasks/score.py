from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(name="app.tasks.score.classify_brand_safety", bind=True)
def classify_brand_safety(self, campaign_id: str, content: dict) -> dict:
    """Keyword blocklist Pass 1 → LLM Pass 2 classification. Owner: AI/DevOps.
    Returns {risks: {hate_speech, misinformation, scam, ...}, reasons[], source_url}."""
    raise NotImplementedError("Day 3 task")


@celery_app.task(name="app.tasks.score.score_influencer", bind=True)
def score_influencer(self, campaign_id: str, influencer_id: str, sub_scores: dict) -> dict:
    """Normalize sub-scores → weighted final score → grade. Owner: AI/DevOps.
    Returns {final_score, grade, confidence, score_version, computed_at}."""
    raise NotImplementedError("Day 4 task")
