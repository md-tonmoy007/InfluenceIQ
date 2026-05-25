from __future__ import annotations

from celery import shared_task


@shared_task(name="app.tasks.crawl.fetch_page", bind=True)
def fetch_page(self, campaign_id: str, url: str) -> dict:
    """URL cache check -> Playwright/HTTPX fetch -> store.
    Returns {url, html, status, cached: bool, fetched_at}."""
    raise NotImplementedError("Day 2 task (Scraping)")


@shared_task(name="app.tasks.crawl.extract_content", bind=True)
def extract_content(self, page: dict) -> dict:
    """HTML clean + metadata + social link discovery handled by scraping_service.
    Returns {url, title, content, social_links[], metadata}."""
    raise NotImplementedError("Day 5 task (Scraping)")
