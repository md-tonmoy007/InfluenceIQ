"""Crawl-phase Celery tasks."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.core.celery.app import celery_app
from sqlalchemy.exc import OperationalError

from backend.core.database import models
from backend.pipeline.content.content_extractor import extract_role4_content
from backend.pipeline.content.fetcher import fetch_url
from backend.pipeline.events import (
    ContentExtracted,
    CrawlFailed,
    PageFetched,
)
from backend.pipeline.tasks._common import (
    db_session,
    mark_campaign_failed,
    publish_event,
    refresh_campaign_status,
    set_phase,
)

log = logging.getLogger(__name__)


@celery_app.task(name="backend.pipeline.tasks.crawl.fetch_page", bind=True, max_retries=3)
def fetch_page(self, campaign_id: str, crawl_source_id: str) -> dict:
    """Fetch the URL behind a ``CrawlSource`` row and persist the HTML."""
    log.info("fetch_page campaign_id=%s crawl_source_id=%s", campaign_id, crawl_source_id)
    with db_session() as session:
        source = session.get(models.CrawlSource, crawl_source_id)
        if source is None:
            log.warning("fetch_page: source %s vanished", crawl_source_id)
            return {"crawl_source_id": crawl_source_id, "status": "missing"}
        url = source.url
        title_hint = source.title

    try:
        page = fetch_url(url)
    except Exception as exc:
        log.warning("fetch_url transient failure for %s: %s", url, exc)
        try:
            raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 30))
        except self.MaxRetriesExceededError:
            _mark_failed(campaign_id, crawl_source_id, str(exc))
            return {"crawl_source_id": crawl_source_id, "status": "failed", "error": str(exc)}

    status_code = page.get("status", 0)
    html = page.get("html", "")
    error = page.get("error")
    if status_code >= 500 and not html:
        msg = error or f"status {status_code}"
        try:
            raise self.retry(exc=RuntimeError(msg), countdown=min(2 ** self.request.retries, 30))
        except self.MaxRetriesExceededError:
            _mark_failed(campaign_id, crawl_source_id, msg)
            return {"crawl_source_id": crawl_source_id, "status": "failed", "error": msg}

    with db_session() as session:
        source = session.get(models.CrawlSource, crawl_source_id)
        if source is None:
            return {"crawl_source_id": crawl_source_id, "status": "missing"}
        source.status = "scraped"
        source.html = html
        source.error_message = error
        if title_hint and not source.title:
            source.title = title_hint
        source.fetched_at = datetime.now(UTC)
        refresh_campaign_status(session, campaign_id)

    publish_event(
        campaign_id,
        "page.fetched",
        **PageFetched(
            campaign_id=campaign_id,
            crawl_source_id=crawl_source_id,
            url=url,
            status=status_code,
            cached=bool(page.get("cached", False)),
        ).to_payload(),
    )
    set_phase(campaign_id, urls_scraped=_bump_counter(campaign_id, "urls_scraped"))

    extract_content.delay(campaign_id, crawl_source_id, page)
    return {"crawl_source_id": crawl_source_id, "status": "scraped", "url": url}


@celery_app.task(name="backend.pipeline.tasks.crawl.extract_content", bind=True, max_retries=2)
def extract_content(self, campaign_id: str, crawl_source_id: str, page: dict) -> dict:
    """Extract structured content from a fetched page and persist it."""
    log.info("extract_content campaign_id=%s crawl_source_id=%s", campaign_id, crawl_source_id)
    try:
        content = extract_role4_content(page)
    except Exception as exc:
        log.exception("extract_role4_content failed for %s: %s", crawl_source_id, exc)
        _mark_failed(campaign_id, crawl_source_id, f"extract_content: {exc}")
        return {"crawl_source_id": crawl_source_id, "status": "failed", "error": str(exc)}

    with db_session() as session:
        source = session.get(models.CrawlSource, crawl_source_id)
        if source is None:
            return {"crawl_source_id": crawl_source_id, "status": "missing"}
        source.title = content.get("title") or source.title
        source.content = content.get("content", "")
        source.status = "extracted"
        if source.html is None:
            source.html = page.get("html", "")
        if not source.relevance_score:
            source.relevance_score = content.get("metrics", {}).get("average_engagement")
        refresh_campaign_status(session, campaign_id)

    publish_event(
        campaign_id,
        "content.extracted",
        **ContentExtracted(
            campaign_id=campaign_id,
            crawl_source_id=crawl_source_id,
            url=content.get("url"),
            title=content.get("title"),
            social_links=content.get("social_links", []),
            metrics=content.get("metrics", {}),
        ).to_payload(),
    )

    from backend.pipeline.tasks.extract import extract_influencers

    extract_influencers.delay(campaign_id, crawl_source_id, content)
    return {
        "crawl_source_id": crawl_source_id,
        "status": "extracted",
        "title": content.get("title"),
    }


def _mark_failed(campaign_id: str, crawl_source_id: str, error: str) -> None:
    try:
        with db_session() as session:
            source = session.get(models.CrawlSource, crawl_source_id)
            if source is None:
                return
            source.status = "failed"
            source.error_message = error
            mark_campaign_failed(session, campaign_id, error)
        publish_event(
            campaign_id,
            "crawl.failed",
            **CrawlFailed(
                campaign_id=campaign_id,
                crawl_source_id=crawl_source_id,
                error=error,
            ).to_payload(),
        )
        set_phase(campaign_id, urls_failed=_bump_counter(campaign_id, "urls_failed"))
    except OperationalError:
        log.exception("Cannot mark %s failed: DB unreachable", crawl_source_id)


def _bump_counter(campaign_id: str, field: str) -> int:
    from backend.core.cache.pipeline_state import increment_pipeline_counter

    return increment_pipeline_counter(campaign_id, field)


__all__ = ["extract_content", "fetch_page"]
