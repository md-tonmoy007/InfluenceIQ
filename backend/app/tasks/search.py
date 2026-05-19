from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(name="app.tasks.search.generate_queries", bind=True)
def generate_queries(self, campaign_id: str) -> list[str]:
    """LLM query generation. Owner: AI/DevOps. Returns list of search query strings."""
    raise NotImplementedError("Day 3 task")


@celery_app.task(name="app.tasks.search.execute_search", bind=True)
def execute_search(self, campaign_id: str, query: str) -> list[dict]:
    """Brave/OpenSerp API call. Owner: Scraping. Returns [{url,title,snippet,relevance}]."""
    raise NotImplementedError("Day 1-2 task (Scraping)")
