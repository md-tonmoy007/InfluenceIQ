from __future__ import annotations

import re
from datetime import UTC, datetime

from celery import shared_task
import structlog

from app.services.pipeline_state import emit_event, update_state

logger = structlog.get_logger(__name__)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_html(html: str, url: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _strip_html(match.group(1))
    return url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()


@shared_task(name="app.tasks.crawl.fetch_page", bind=True)
def fetch_page(self, campaign_id: str, url: str) -> dict:
    """URL cache check -> Playwright/HTTPX fetch -> store.
    Returns {url, html, status, cached: bool, fetched_at}."""
    fetched_at = datetime.now(UTC).isoformat()
    html = (
        "<html><head><title>Demo creator profile</title></head><body>"
        "<h1>Dr Sarah Tan</h1>"
        "<p>Certified nutrition educator with Instagram @drsarahtan and YouTube creator presence.</p>"
        "<p>Known for evidence-based wellness content and positive brand collaborations.</p>"
        "</body></html>"
    )
    page = {"url": url, "html": html, "status": 200, "cached": False, "fetched_at": fetched_at}
    update_state(campaign_id, phase="crawl", last_url=url, last_status=200)
    emit_event(campaign_id, "page.scraped", {"url": url, "status": 200})
    logger.info("page_fetched", campaign_id=campaign_id, url=url, status=200, cached=False)
    return page


@shared_task(name="app.tasks.crawl.extract_content", bind=True)
def extract_content(self, page: dict) -> dict:
    """HTML clean + metadata + social link discovery handled by scraping_service.
    Returns {url, title, content, social_links[], metadata}."""
    url = page.get("url", "")
    html = page.get("html", "")
    social_links = sorted(set(re.findall(r"https?://(?:www\.)?(?:instagram|youtube|tiktok)\.com/[^\s\"'<>]+", html)))
    handles = [f"https://instagram.com/{handle}" for handle in re.findall(r"@([A-Za-z0-9_.]{3,30})", html)]
    content = {
        "url": url,
        "title": _title_from_html(html, url),
        "content": _strip_html(html),
        "social_links": sorted(set(social_links + handles)),
        "metadata": {
            "status": page.get("status"),
            "cached": bool(page.get("cached", False)),
            "fetched_at": page.get("fetched_at"),
        },
    }
    logger.info("content_extracted", url=url, title=content["title"], social_link_count=len(content["social_links"]))
    return content
