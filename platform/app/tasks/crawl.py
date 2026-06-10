from __future__ import annotations

from celery import shared_task

from app.config import settings
from app.services.crawl_policy import select_discovered_links
from app.services.pipeline_state import emit_event, update_state
from scraping_service.crawling.content_extractor import extract_role5_content
from scraping_service.crawling.fetcher import fetch_url
from scraping_service.crawling.rate_limiter import throttle_delay_seconds


@shared_task(name="app.tasks.crawl.fetch_page", bind=True)
def fetch_page(
    self,
    campaign_id: str,
    url: str,
    *,
    depth: int = 1,
    source_type: str = "search_result",
    parent_url: str = "",
) -> dict:
    """Fetch through the scraping service and preserve crawl provenance."""
    wait_for = throttle_delay_seconds(url)
    if wait_for > 0:
        emit_event(campaign_id, "page.rate_limited", {"url": url, "retry_in": wait_for})

    page = fetch_url(url)
    page["depth"] = depth
    page["source_type"] = source_type
    page["parent_url"] = parent_url

    update_state(
        campaign_id,
        phase="crawl",
        last_url=page["url"],
        last_status=page["status"],
        crawl_provider=page.get("provider"),
    )
    if page.get("cached"):
        emit_event(campaign_id, "url.cache_hit", {"url": page["url"]})
    emit_event(
        campaign_id,
        "page.scraped",
        {
            "url": page["url"],
            "status": page["status"],
            "cached": bool(page.get("cached", False)),
            "provider": page.get("provider"),
            "depth": depth,
            "source_type": source_type,
        },
    )
    return page


@shared_task(name="app.tasks.crawl.extract_content", bind=True)
def extract_content(self, page: dict) -> dict:
    """Extract Role-5-ready content through the scraping service."""
    content = extract_role5_content(page)
    content["discovered_links"] = select_discovered_links(
        page.get("html", ""),
        content["url"],
        depth=int(page.get("depth") or 1),
        max_depth=settings.CRAWL_MAX_DEPTH,
    )
    return content
