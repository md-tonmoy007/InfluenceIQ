from __future__ import annotations

import uuid
from urllib.parse import quote_plus

from celery import shared_task
import structlog

from app.db import SessionLocal
from app.models import Campaign
from app.services.pipeline_state import emit_event, update_state

logger = structlog.get_logger(__name__)


def _topic_from_campaign(campaign_id: str) -> str:
    default_topic = "health and wellness creators"
    session = SessionLocal()
    try:
        campaign = session.get(Campaign, uuid.UUID(campaign_id))
    except ValueError:
        campaign = None
    finally:
        session.close()

    if campaign is None:
        return default_topic

    parts = [
        campaign.brand.strip(),
        campaign.product.strip(),
        campaign.category.strip(),
        campaign.goal.strip(),
    ]
    topic = " ".join(part for part in parts if part)
    return topic or default_topic


@shared_task(name="app.tasks.search.generate_queries", bind=True)
def generate_queries(self, campaign_id: str) -> list[str]:
    """LLM query generation handled by ai_agent_services."""
    topic = _topic_from_campaign(campaign_id)
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
    logger.info("queries_generated", campaign_id=campaign_id, query_count=len(queries), topic=topic)
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
    logger.info("search_executed", campaign_id=campaign_id, query=query, result_count=len(results))
    return results
