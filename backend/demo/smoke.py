from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.demo.schemas import QueryGenRequest, ScrapeRequest, SearchFilterRequest
from backend.pipeline.content.content_extractor import extract_role4_content
from backend.pipeline.content.fetcher import fetch_url
from backend.pipeline.content.search_providers import search_web
from backend.pipeline.extraction.entities import extract_influencer_mentions
from backend.pipeline.tasks.extract import _llm_extract_handles, _normalize_llm_mentions
from backend.pipeline.tasks.search import (
    _flag,
    _generate_planned_queries,
    _llm_filter_urls,
    _llm_generate_queries,
    _query_model_override,
)


def run_query_generation(req: QueryGenRequest) -> dict[str, Any]:
    """Exercise query planning without persisting a campaign."""
    from backend.ml.models.registry import registry

    payload = req.model_dump()
    llm_queries = _llm_generate_queries(payload)
    queries = _generate_planned_queries(payload)

    reg = registry()
    backend_name = reg.resolve_name("llm")
    try:
        info = reg.get(backend_name).info()
        backend_info = {"name": info.name, "model": info.version, "loaded": info.loaded}
    except Exception as exc:  # noqa: BLE001 — diagnostics endpoint
        backend_info = {"name": backend_name, "error": str(exc)}

    return {
        "queries": queries,
        "count": len(queries),
        "source": "llm" if llm_queries is not None else "deterministic",
        "llm_enabled": _flag("AI_AGENT_LLM_QUERY_PLANNING"),
        "model_override": _query_model_override(),
        "backend": backend_info,
    }


def run_search_filter(req: SearchFilterRequest) -> dict[str, Any]:
    """Run a single SERP search and LLM URL filter without persisting."""
    payload = req.model_dump(exclude={"query"})
    raw_results = search_web(req.query, limit=10)
    filtered_results = _llm_filter_urls(raw_results, payload)
    providers_used = list({r.get("provider", "unknown") for r in raw_results})

    return {
        "query": req.query,
        "serp_api_enabled": bool(settings.SERP_API_KEY),
        "llm_filter_enabled": _flag("AI_AGENT_LLM_QUERY_PLANNING"),
        "model_override": _query_model_override(),
        "providers_used": providers_used,
        "raw": {"count": len(raw_results), "results": raw_results},
        "filtered": {
            "count": len(filtered_results),
            "kept": len(filtered_results),
            "dropped": len(raw_results) - len(filtered_results),
            "results": filtered_results,
        },
    }


def run_scrape(req: ScrapeRequest) -> dict[str, Any]:
    """Fetch a URL and run extraction without persisting."""
    page = fetch_url(req.url)
    content = extract_role4_content(page)
    source_url = str(content.get("url") or req.url)

    llm_items = _llm_extract_handles(content)
    if llm_items is not None:
        mentions = _normalize_llm_mentions(llm_items, source_url)
        extraction_method = "llm"
    else:
        mentions = extract_influencer_mentions(content)
        extraction_method = "regex_fallback"

    return {
        "url": req.url,
        "scrape_do_enabled": bool(settings.SCRAPE_DO_API),
        "provider": page.get("provider"),
        "status": page.get("status"),
        "error": page.get("error"),
        "cached": page.get("cached", False),
        "title": content.get("title"),
        "content_preview": (content.get("content") or "")[:500],
        "extraction_method": extraction_method,
        "influencer_mentions": {"count": len(mentions), "mentions": mentions},
    }
