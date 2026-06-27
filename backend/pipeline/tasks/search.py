"""Search-phase Celery tasks."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
from typing import Any
from uuid import uuid4

from backend.core.celery.app import celery_app
from sqlalchemy.exc import SQLAlchemyError

from backend.core.database import models
from backend.pipeline.content.search_providers import search_web
from backend.pipeline.events import QueryGenerationCompleted, SearchExecuted, SearchFailed
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


_FALSEY = frozenset({"", "0", "false", "no", "off"})
_BOOLEAN = frozenset({"1", "true", "yes", "on"}) | _FALSEY


def _flag(name: str) -> bool:
    """Truthy if env is set to anything other than a falsey token.

    Note ``AI_AGENT_LLM_QUERY_PLANNING`` doubles as a model selector: a
    value like ``openai/gpt-oss-20b:free`` enables the LLM path *and* is
    used as the per-request model override (see :func:`_query_model_override`).
    """
    return os.environ.get(name, "").strip().lower() not in _FALSEY


def _query_model_override() -> str | None:
    """Return the model id when ``AI_AGENT_LLM_QUERY_PLANNING`` holds one.

    A bare boolean toggle (``1``/``true``/...) returns ``None`` so the
    adapter's configured default model is used.
    """
    raw = os.environ.get("AI_AGENT_LLM_QUERY_PLANNING", "").strip()
    if not raw or raw.lower() in _BOOLEAN:
        return None
    return raw


def _run_predict(result: Any) -> Any:
    """Resolve a possibly-async ``predict_text`` result in a sync task."""
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


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
    locations = payload.get("locations") or []

    queries: list[str] = []
    location_suffix = f" {' '.join(locations[:2])}".strip() if locations else ""
    if product and niche:
        queries.append(f"{product} {niche} influencers{location_suffix}".strip())
    if niche:
        queries.append(f"top {niche} creators{location_suffix}".strip())
    if product:
        queries.append(f"{product} reviews and recommendations{location_suffix}".strip())
    if audience and niche:
        queries.append(f"{niche} creators for {audience}{location_suffix}".strip())
    if goals and niche:
        queries.append(f"{niche} influencers {goals}{location_suffix}".strip())
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
        # Budget headroom: reasoning models (e.g. gpt-oss) spend the early
        # tokens on a reasoning trace, so a tight cap yields empty content.
        # 1024 stays well under TOKEN_BUDGET_QUERY_GEN (2000).
        text = _run_predict(
            llm_backend.predict_text(  # type: ignore[union-attr]
                prompt, max_tokens=1024, temperature=0.3, model=_query_model_override()
            )
        )
        if not text or text.startswith("[stub:"):
            return None

        import json
        parsed = json.loads(_strip_code_fence(text))
        queries_raw = parsed if isinstance(parsed, list) else parsed.get("queries", [])
        queries = [str(q).strip() for q in queries_raw if q and str(q).strip()]
        return queries[:5] if len(queries) >= 3 else None
    except Exception:
        return None


def _strip_code_fence(text: str) -> str:
    """Strip a leading ```json / ``` fence some models wrap JSON in."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


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


def _build_url_filter_prompt(results: list[dict], payload: dict[str, Any]) -> str:
    product = payload.get("product", "").strip()
    niche = payload.get("niche", "").strip()
    goals = payload.get("goals", "").strip()
    audience = payload.get("target_audience", "").strip()
    platforms = payload.get("preferred_platforms") or []
    platform_str = ", ".join(platforms) if platforms else "any"

    lines = [
        "You are a research assistant selecting web pages that are likely to contain "
        "influencer or creator profile information relevant to the campaign below.\n",
        f"Campaign brief:",
        f"  Product/Service: {product or '(not specified)'}",
        f"  Niche: {niche or '(not specified)'}",
        f"  Goals: {goals or '(not specified)'}",
        f"  Target audience: {audience or '(not specified)'}",
        f"  Preferred platforms: {platform_str}\n",
        "Search results (index | url | title | snippet):",
    ]
    for i, r in enumerate(results):
        snippet = (r.get("snippet") or "")[:120].replace("\n", " ")
        lines.append(f"  {i} | {r.get('url', '')} | {r.get('title', '')} | {snippet}")

    lines += [
        "",
        "Select ONLY the URLs that are likely to contain information about specific "
        "influencers, creators, or content creators relevant to this campaign.",
        "INCLUDE: influencer/creator profiles, bio pages, interview articles, creator "
        "directories, social media pages, industry expert listings.",
        "EXCLUDE: e-commerce product pages, brand news, generic informational articles, "
        "search-result index pages, ads, wikis unrelated to people.",
        "Return ONLY a JSON array of the selected URL strings, no other text.",
    ]
    return "\n".join(lines)


def _llm_filter_urls(results: list[dict], payload: dict[str, Any]) -> list[dict]:
    """Use the LLM to keep only influencer-relevant URLs from search results.

    Falls back to returning all results when the LLM is disabled, unavailable,
    returns an empty selection, or any error occurs.
    """
    if not _flag("AI_AGENT_LLM_QUERY_PLANNING") or not results:
        return results
    try:
        from backend.ml.contracts import TextInferenceRequest  # noqa: F401
        from backend.ml.models.registry import registry

        reg = registry()
        llm_backend = reg.get(reg.resolve_name("llm"))
        if llm_backend is None or not hasattr(llm_backend, "predict_text"):
            return results

        prompt = _build_url_filter_prompt(results, payload)
        text = _run_predict(
            llm_backend.predict_text(
                prompt, max_tokens=512, temperature=0.1, model=_query_model_override()
            )
        )
        if not text or text.startswith("[stub:"):
            return results

        import json
        selected_urls: set[str] = set(json.loads(_strip_code_fence(text)))
        if not selected_urls:
            return results

        filtered = [r for r in results if r.get("url") in selected_urls]
        log.info(
            "llm_filter_urls kept=%d of total=%d",
            len(filtered),
            len(results),
        )
        return filtered if filtered else results
    except Exception:
        return results


@celery_app.task(name="backend.pipeline.tasks.search.generate_queries", bind=True, max_retries=2)
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

    for index, query in enumerate(queries):
        execute_search.delay(campaign_id, query, index)

    publish_event(
        campaign_id,
        "query.generation.completed",
        **QueryGenerationCompleted(
            campaign_id=campaign_id,
            query_count=len(queries),
            queries=queries,
        ).to_payload(),
    )

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


@celery_app.task(name="backend.pipeline.tasks.search.execute_search", bind=True, max_retries=3)
def execute_search(self, campaign_id: str, query: str, index: int = 0) -> dict:
    """Run a single web search and materialise the results as ``CrawlSource`` rows."""
    log.info("execute_search campaign_id=%s query=%r", campaign_id, query)
    limit = 8
    try:
        results = search_web(query, limit=limit)
        with db_session() as session:
            campaign = get_campaign(session, campaign_id)
            _payload = campaign_query_payload(campaign)
        results = _llm_filter_urls(results, _payload)
    except Exception as exc:
        log.exception("search_web failed campaign_id=%s query=%r: %s", campaign_id, query, exc)
        publish_event(
            campaign_id,
            "search.failed",
            **SearchFailed(
                campaign_id=campaign_id,
                query=query,
                index=index,
                error=str(exc),
            ).to_payload(),
        )
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
        **SearchExecuted(
            campaign_id=campaign_id,
            query=query,
            index=index,
            result_count=len(results),
            crawl_source_ids=created_ids,
        ).to_payload(),
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
