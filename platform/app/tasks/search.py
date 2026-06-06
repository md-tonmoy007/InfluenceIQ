from __future__ import annotations

from urllib.parse import quote_plus

from celery import shared_task

from app.services.pipeline_state import emit_event, update_state


def _topic_from_campaign_id(campaign_id: str) -> str:
    cleaned = campaign_id.replace("-", " ").replace("_", " ").strip()
    if not cleaned or cleaned.lower() in {"demo", "test"}:
        return "health and wellness creators"
    return cleaned


@shared_task(name="app.tasks.search.generate_queries", bind=True)
def generate_queries(self, campaign_id: str) -> list[str]:
    """LLM query generation handled by ai_agent_services."""
    topic = _topic_from_campaign_id(campaign_id)
    queries = [
        f"{topic} influencers",
        f"{topic} creators Instagram",
        f"{topic} YouTube experts",
        f"{topic} TikTok educators",
        f"{topic} brand safe creators",
        f"{topic} certified professionals social media",
    ]
    update_state(campaign_id, phase="search", generated_query_count=len(queries))
    emit_event(campaign_id, "query.generated", {"queries": queries})
    return queries


@shared_task(name="app.tasks.search.execute_search", bind=True)
def execute_search(self, campaign_id: str, query: str) -> list[dict]:
    """Search API execution handled by scraping_service."""
    slug = quote_plus(query.lower())
    results = [
        {
            "url": f"https://example.com/influencers/{slug}",
            "title": f"Top creators for {query}",
            "snippet": f"Demo search result for {query}.",
            "relevance_score": 82,
        },
        {
            "url": f"https://example.com/profiles/{slug}",
            "title": f"Verified profiles matching {query}",
            "snippet": f"Candidate creator profiles for {query}.",
            "relevance_score": 76,
        },
    ]
    update_state(campaign_id, phase="search", last_query=query, discovered_url_count=len(results))
    for result in results:
        emit_event(
            campaign_id,
            "url.discovered",
            {
                "url": result["url"],
                "title": result["title"],
                "relevance": result["relevance_score"],
            },
        )
    return results
