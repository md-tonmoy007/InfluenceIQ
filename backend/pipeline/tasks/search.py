"""Search-phase Celery tasks."""

from __future__ import annotations

import logging
import os
import re
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
    mark_campaign_failed,
    publish_event,
    refresh_campaign_status,
    set_phase,
)

log = logging.getLogger(__name__)


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in frozenset({"1", "true", "yes", "on"})


def _normalize_tokens(text: str) -> set[str]:
    """Lowercase, split on non-alpha, and return a set of tokens."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity of the token sets of two strings."""
    tokens_a = _normalize_tokens(a)
    tokens_b = _normalize_tokens(b)
    if not tokens_a and not tokens_b:
        return 1.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def dedupe_queries(queries: list[str], threshold: float = 0.8) -> list[str]:
    """Remove near-duplicate queries whose normalised token-set Jaccard
    similarity is >= *threshold*. Earlier queries are preferred.
    """
    deduped: list[str] = []
    for query in queries:
        if any(_jaccard_similarity(query, kept) >= threshold for kept in deduped):
            continue
        deduped.append(query)
    return deduped


def _ensure_platform_coverage(queries: list[str],
                              platforms: list[str] | None) -> list[str]:
    """Ensure at least one query targets each preferred platform.

    If a platform is not already hinted in any query (e.g. "youtube"
    appearing in the text), the first un-tagged query gets the platform
    appended.
    """
    if not platforms:
        return queries
    platform_names = {p.lower().strip() for p in platforms}
    covered: set[str] = set()
    for query in queries:
        for p in list(platform_names):
            if p in query.lower():
                covered.add(p)
    missing = platform_names - covered
    if not missing:
        return queries

    result = list(queries)
    for platform in missing:
        for i, q in enumerate(result):
            if platform not in q.lower():
                result[i] = f"{q} {platform}"
                break
    return result


def _build_query_set(payload: dict[str, Any]) -> list[str]:
    """Expand a campaign payload into 3-5 web-search queries."""
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

    tagged: list[str] = []
    for query in queries[:5]:
        if platforms and "youtube" in platforms and "youtube" not in query.casefold():
            tagged.append(f"{query} youtube")
        else:
            tagged.append(query)
    return tagged


def _llm_generate_queries(payload: dict[str, Any]) -> list[str] | None:
    """Optional LLM path for query generation.

    Reads ``AI_AGENT_LLM_QUERY_PLANNING=1``. On success returns a list
    of 3-5 queries. On error or empty result returns ``None`` so the
    caller falls back to :func:`_build_query_set`.
    """
    if not _flag("AI_AGENT_LLM_QUERY_PLANNING"):
        return None

    try:
        from backend.ml.contracts import TextInferenceRequest
        from backend.ml.models.registry import registry

        reg = registry()
        llm_backend = reg.get(reg.resolve_name("llm"))
        if llm_backend is None or not hasattr(llm_backend, "predict_text"):
            return None

        prompt = _build_llm_query_prompt(payload)
        text = llm_backend.predict_text(prompt, max_tokens=256, temperature=0.3)  # type: ignore[union-attr]
        if not text or text.startswith("[stub:"):
            return None

        import json
        parsed = json.loads(text)
        queries_raw = parsed if isinstance(parsed, list) else parsed.get("queries", [])
        queries = [str(q).strip() for q in queries_raw if q and str(q).strip()]
        return queries[:5] if len(queries) >= 3 else None
    except Exception:
        return None


def _build_llm_query_prompt(payload: dict[str, Any]) -> str:
    """Build a prompt asking the LLM to produce campaign-specific search queries."""
    product = payload.get("product", "").strip()
    niche = payload.get("niche", "").strip()
    goals = payload.get("goals", "").strip()
    audience = payload.get("target_audience", "").strip()
    platforms = payload.get("preferred_platforms", [])
    platform_str = ", ".join(platforms) if platforms else "any"

    return (
        "You are a campaign search-query planner. Generate 3-5 "
        "specific, diverse web-search queries to find relevant "
        "influencers and creators for the following campaign brief. "
        "Return ONLY a JSON array of strings, no other text.\n\n"
        f"Product/Service: {product or '(not specified)'}\n"
        f"Niche: {niche or '(not specified)'}\n"
        f"Goals: {goals or '(not specified)'}\n"
        f"Target audience: {audience or '(not specified)'}\n"
        f"Preferred platforms: {platform_str}\n"
    )


@shared_task(name="backend.pipeline.tasks.search.generate_queries", bind=True, max_retries=2)
def generate_queries(self, campaign_id: str) -> dict:
    """Generate search queries for a campaign and fan out to :func:`execute_search`."""
    log.info("generate_queries start campaign_id=%s", campaign_id)
    with db_session() as session:
        campaign = get_campaign(session, campaign_id)
        campaign.status = "running"
        campaign.started_at = campaign.started_at or campaign.created_at
        campaign.failed_at = None
        campaign.failure_reason = None
        payload = campaign_query_payload(campaign)
        queries = _generate_planned_queries(payload)
        set_phase(campaign_id, phase="query_generation", urls_discovered=len(queries))
        publish_event(campaign_id, "query.generation.completed", query_count=len(queries), queries=queries)

    for index, query in enumerate(queries):
        execute_search.delay(campaign_id, query, index)

    return {"campaign_id": campaign_id, "queries": queries, "count": len(queries)}


def _generate_planned_queries(payload: dict[str, Any]) -> list[str]:
    """Generate deduplicated, platform-diversified queries.

    Tries the LLM path first when the flag is set. Falls back to the
    deterministic :func:`_build_query_set`. Always applies dedup and
    platform coverage.
    """
    platforms = payload.get("preferred_platforms") or []
    queries = _llm_generate_queries(payload)
    if queries is None:
        queries = _build_query_set(payload)
    queries = dedupe_queries(queries)
    queries = _ensure_platform_coverage(queries, platforms)
    return queries[:5]


@shared_task(name="backend.pipeline.tasks.search.execute_search", bind=True, max_retries=3)
def execute_search(self, campaign_id: str, query: str, index: int = 0) -> dict:
    """Run a single web search and materialise the results as ``CrawlSource`` rows."""
    log.info("execute_search campaign_id=%s query=%r", campaign_id, query)
    limit = 8
    try:
        results = search_web(query, limit=limit)
    except Exception as exc:
        log.exception("search_web failed campaign_id=%s query=%r: %s", campaign_id, query, exc)
        publish_event(campaign_id, "search.failed", query=query, index=index, error=str(exc))
        with db_session() as session:
            mark_campaign_failed(session, campaign_id, str(exc))
        raise

    created_ids: list[str] = []
    with db_session() as session:
        for result in results:
            url = result.get("url")
            if not url:
                continue
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
        refresh_campaign_status(session, campaign_id)

    publish_event(
        campaign_id,
        "search.executed",
        query=query,
        index=index,
        result_count=len(results),
        crawl_source_ids=created_ids,
    )
    set_phase(campaign_id, urls_discovered=len(created_ids))

    for crawl_source_id in created_ids:
        from backend.pipeline.tasks.crawl import fetch_page

        fetch_page.delay(campaign_id, crawl_source_id)

    return {
        "campaign_id": campaign_id,
        "query": query,
        "index": index,
        "crawl_source_ids": created_ids,
    }


__all__ = [
    "dedupe_queries",
    "execute_search",
    "generate_queries",
    "_build_query_set",
    "_generate_planned_queries",
    "_ensure_platform_coverage",
]
