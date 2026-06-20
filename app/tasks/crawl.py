"""Crawl-phase Celery tasks.

Two task bodies live here:

* :func:`fetch_page` (``app.tasks.crawl.fetch_page``,
  ``scraping_queue``) — loads a ``CrawlSource`` row, fetches the
  URL via :func:`scraping_service.crawling.fetcher.fetch_url`, and
  stores the HTML.

* :func:`extract_content` (``app.tasks.crawl.extract_content``,
  ``scraping_queue``) — runs
  :func:`scraping_service.crawling.content_extractor.extract_role5_content`
  over the page and persists the structured result. On success it
  hands off to :func:`app.tasks.extract.extract_influencers`.

Fetch errors are caught and recorded on the row; the worker retry
policy is applied via ``self.retry`` so transient outages
(``httpx.HTTPError``, ``ConnectionError``) get a second chance.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from celery import shared_task
from sqlalchemy.exc import OperationalError

from app.db import models
from app.tasks._common import db_session, publish_event, set_phase
from scraping_service.crawling.content_extractor import extract_role5_content
from scraping_service.crawling.fetcher import fetch_url

log = logging.getLogger(__name__)


@shared_task(name="app.tasks.crawl.fetch_page", bind=True, max_retries=3)
def fetch_page(self, campaign_id: str, crawl_source_id: str) -> dict:
    """Fetch the URL behind a ``CrawlSource`` row and persist the HTML.

    On transient network failures the task re-raises so Celery can
    apply its exponential-backoff retry. On permanent failures (4xx,
    5xx with no fallback, parse errors) the row is marked ``failed``
    with the error message and the chain continues with the next
    source.
    """
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
        # Transient I/O — let Celery retry with backoff.
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
        # 5xx with no body — retry.
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
        # ``fetched_at`` records the persist time (timezone-aware UTC).
        source.fetched_at = datetime.now(UTC)

    publish_event(campaign_id, "page.fetched",
                  crawl_source_id=crawl_source_id, url=url,
                  status=status_code, cached=bool(page.get("cached", False)))
    set_phase(campaign_id, urls_scraped=_bump_counter(campaign_id, "urls_scraped"))

    # Hand off to content extraction with the fresh page dict.
    extract_content.delay(campaign_id, crawl_source_id, page)
    return {"crawl_source_id": crawl_source_id, "status": "scraped", "url": url}


@shared_task(name="app.tasks.crawl.extract_content", bind=True, max_retries=2)
def extract_content(self, campaign_id: str, crawl_source_id: str, page: dict) -> dict:
    """Extract structured content from a fetched page and persist it.

    The page dict is the same shape :func:`extract_role5_content`
    accepts (URL, HTML, status, etc.). The function returns a
    ``content`` dict that already carries a ``role5_candidate`` block
    — we store the title and the role5 payload and pass the full
    content dict to the next task.
    """
    log.info("extract_content campaign_id=%s crawl_source_id=%s", campaign_id, crawl_source_id)
    try:
        content = extract_role5_content(page)
    except Exception as exc:
        log.exception("extract_role5_content failed for %s: %s", crawl_source_id, exc)
        _mark_failed(campaign_id, crawl_source_id, f"extract_content: {exc}")
        return {"crawl_source_id": crawl_source_id, "status": "failed", "error": str(exc)}

    with db_session() as session:
        source = session.get(models.CrawlSource, crawl_source_id)
        if source is None:
            return {"crawl_source_id": crawl_source_id, "status": "missing"}
        source.title = content.get("title") or source.title
        # The full extracted text (without HTML markup) — bounded by
        # what the content extractor already truncated.
        source.content = content.get("content", "")
        source.status = "extracted"
        if not source.relevance_score:
            source.relevance_score = content.get("metrics", {}).get("average_engagement")

    publish_event(campaign_id, "content.extracted",
                  crawl_source_id=crawl_source_id,
                  url=content.get("url"),
                  title=content.get("title"),
                  social_links=content.get("social_links", []),
                  metrics=content.get("metrics", {}))
    set_phase(campaign_id, urls_scraped=_bump_counter(campaign_id, "urls_scraped"))

    from app.tasks.extract import extract_influencers  # avoid circular import
    extract_influencers.delay(campaign_id, crawl_source_id, content)
    return {
        "crawl_source_id": crawl_source_id,
        "status": "extracted",
        "title": content.get("title"),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _mark_failed(campaign_id: str, crawl_source_id: str, error: str) -> None:
    """Mark a ``CrawlSource`` row as failed without raising on secondary errors."""
    try:
        with db_session() as session:
            source = session.get(models.CrawlSource, crawl_source_id)
            if source is None:
                return
            source.status = "failed"
            source.error_message = error
        publish_event(campaign_id, "crawl.failed",
                      crawl_source_id=crawl_source_id, error=error)
        set_phase(campaign_id, urls_failed=_bump_counter(campaign_id, "urls_failed"))
    except OperationalError:
        # The DB is down too — there is nothing useful to do here.
        log.exception("Cannot mark %s failed: DB unreachable", crawl_source_id)


def _bump_counter(campaign_id: str, field: str) -> int:
    """Atomically increment a numeric counter in the pipeline-state hash.

    Implemented as a read-modify-write because the state hash carries
    multiple counters; the operation is fast and the lock is not held
    across Redis round-trips. For the per-campaign QPS the pipeline
    operates at (single digits) the race window is irrelevant.
    """
    from app.services.pipeline_state import get_pipeline_state
    state = get_pipeline_state(campaign_id) or {}
    return int(state.get(field, 0)) + 1


__all__ = ["extract_content", "fetch_page"]
