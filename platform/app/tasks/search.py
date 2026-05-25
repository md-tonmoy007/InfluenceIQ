from __future__ import annotations

from celery import shared_task


@shared_task(name="app.tasks.search.generate_queries", bind=True)
def generate_queries(self, campaign_id: str) -> list[str]:
    """LLM query generation handled by ai_agent_services."""
    raise NotImplementedError("Day 3 task")


@shared_task(name="app.tasks.search.execute_search", bind=True)
def execute_search(self, campaign_id: str, query: str) -> list[dict]:
    """Search API execution handled by scraping_service."""
    raise NotImplementedError("Day 1-2 task (Scraping)")
