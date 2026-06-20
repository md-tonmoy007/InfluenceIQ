"""Search-phase Celery tasks.

Two task bodies live here:

* :func:`generate_queries` (``backend.pipeline.tasks.search.generate_queries``,
  ``ai_agent_queue``) — turns a campaign into a list of web-search
  queries and dispatches :func:`execute_search` for each.

* :func:`execute_search` (``backend.pipeline.tasks.search.execute_search``,
  ``scraping_queue``) — runs :func:`backend.pipeline.content.search_providers.search_web`
  and creates a ``CrawlSource`` row per result with status ``pending``.

The query generator is intentionally deterministic in v1 — it
expands the campaign into a small set of fixed-shape queries using
the campaign fields. The LLM-driven query generation is opt-in via
the ``AI_AGENT_QUERY_LLM=1`` env flag; the LLM path is reserved for a
follow-up because it requires provider wiring.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from backend.core.database import models
from backend.pipeline.content.search_providers import search_web
from backend.pipeline.tasks._common import (
    campaign_query_payload,
    db_session,
    get_campaign,
    publish_event,
    set_phase,
)

log = logging.getLogger(__name__)


def _build_query_set(payload: dict[str, Any]) -> list[str]:
    """Expand a campaign payload into 3-5 web-search queries.

    Deterministic: no LLM, no random sampling. The same campaign
    always produces the same query set so re-running the task is
    idempotent.
    """
    product = (payload.get("product") or "").strip()
    niche = (payload.get("niche") or "").strip()
    goals = (payload.get("goals") or "").strip()
    audience = (payload.get("target_audience") or "").strip()
    platforms = payload.get("preferred_platforms") or []

    queries: list[str] = []
    if product and niche:
        queries.append(f"{product} {niche} influencers")
    if niche:
        queries.append(f"top {niche} creators")
    if product:
        queries.append(f"{product} reviews and recommendations")
    if audience and niche:
        queries.append(f"{niche} creators for {audience}")
    if goals and niche:
        queries.append(f"{niche} influencers {goals}".strip())
    if not queries:
        queries.append("trusted creator recommendations")

    # Tag the queries with platform hints when the brand prefers a
    # specific surface so the search provider can weight results.
    tagged: list[str] = []
    for query in queries[:5]:
        if platforms and "youtube" in platforms and "youtube" not in query.casefold():
            tagged.append(f"{query} youtube")
        else:
            tagged.append(query)
    return tagged


@shared_task(name="backend.pipeline.tasks.search.generate_queries", bind=True, max_retries=2)
def generate_queries(self, campaign_id: str) -> dict:
    """Generate search queries for a campaign and fan out to :func:`execute_search`.

    Returns a small dict with the query list so Celery's result backend
    keeps a record. The pipeline state in Redis is the authoritative
    progress tracker; this return value is for observability only.
    """
    log.info("generate_queries start campaign_id=%s", campaign_id)
    with db_session() as session:
        campaign = get_campaign(session, campaign_id)
        payload = campaign_query_payload(campaign)
        queries = _build_query_set(payload)
        # Mark the pipeline state in Redis as soon as we know the count
        # so the WebSocket client sees a real number, not a stale zero.
        set_phase(campaign_id, phase="query_generation", urls_discovered=len(queries))
        publish_event(campaign_id, "query.generation.completed",
                      query_count=len(queries), queries=queries)

    for index, query in enumerate(queries):
        execute_search.delay(campaign_id, query, index)

    return {"campaign_id": campaign_id, "queries": queries, "count": len(queries)}


@shared_task(name="backend.pipeline.tasks.search.execute_search", bind=True, max_retries=3)
def execute_search(self, campaign_id: str, query: str, index: int = 0) -> dict:
    """Run a single web search and materialise the results as ``CrawlSource`` rows.

    For every search hit we:
    1. Insert (or skip, if already present) a ``CrawlSource`` row
       keyed by ``(campaign_id, url)`` — the unique index
       ``idx_crawl_sources_url`` makes the upsert cheap.
    2. Emit a ``search.executed`` event with the result list.
    3. Fan out one :func:`backend.pipeline.tasks.crawl.fetch_page` task per row.

    Search errors are caught and recorded; the worker applies its
    retry policy on transient failures (``httpx.HTTPError``,
    ``ConnectionError``).
    """
    log.info("execute_search campaign_id=%s query=%r", campaign_id, query)
    limit = 8
    try:
        results = search_web(query, limit=limit)
    except Exception as exc:
        log.exception("search_web failed campaign_id=%s query=%r: %s",
                      campaign_id, query, exc)
        publish_event(campaign_id, "search.failed",
                      query=query, index=index, error=str(exc))
        # Re-raise so the worker retry policy fires; transient outages
        # get a second chance, persistent ones land in the DLQ.
        raise

    created_ids: list[str] = []
    with db_session() as session:
        for result in results:
            url = result.get("url")
            if not url:
                continue
            # Idempotent insert: skip rows that already exist for this
            # campaign + url pair. The unique index handles concurrent
            # inserts; here we do a pre-check for cleaner events.
            existing = (
                session.query(models.CrawlSource)
                .filter(
                    models.CrawlSource.campaign_id == campaign_id,
                    models.CrawlSource.url == url,
                )
                .first()
            )
            if existing is not None:
                created_ids.append(str(existing.id))
                continue
            try:
                source = models.CrawlSource(
                    id=uuid4(),
                    campaign_id=campaign_id,
                    url=url,
                    title=result.get("title"),
                    relevance_score=result.get("relevance_score"),
                    status="pending",
                )
                session.add(source)
                session.flush()
                created_ids.append(str(source.id))
            except SQLAlchemyError:
                # Concurrent insert won the race — fall back to the
                # existing row.
                session.rollback()
                existing = (
                    session.query(models.CrawlSource)
                    .filter(
                        models.CrawlSource.campaign_id == campaign_id,
                        models.CrawlSource.url == url,
                    )
                    .first()
                )
                if existing is not None:
                    created_ids.append(str(existing.id))

    publish_event(campaign_id, "search.executed",
                  query=query, index=index,
                  result_count=len(results), crawl_source_ids=created_ids)
    set_phase(campaign_id, urls_discovered=len(created_ids))

    for crawl_source_id in created_ids:
        from backend.pipeline.tasks.crawl import (
            fetch_page,  # local import avoids cycle at import time
        )
        fetch_page.delay(campaign_id, crawl_source_id)

    return {
        "campaign_id": campaign_id,
        "query": query,
        "index": index,
        "crawl_source_ids": created_ids,
    }


__all__ = ["execute_search", "generate_queries"]
