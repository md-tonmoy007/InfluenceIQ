from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote_plus

import httpx

from backend.core.config import settings
from backend.pipeline.content.contracts import SearchResult

SearchFn = Callable[[str, int], list[SearchResult]]


def _dedupe(results: list[SearchResult], limit: int) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for result in sorted(results, key=lambda item: item.relevance_score, reverse=True):
        if result.url in seen:
            continue
        seen.add(result.url)
        out.append(result.to_dict())
        if len(out) >= limit:
            break
    return out


def _serp_api_search(query: str, limit: int) -> list[SearchResult]:
    if not settings.SERP_API_KEY:
        return []
    response = httpx.get(
        "https://serpapi.com/search.json",
        params={"api_key": settings.SERP_API_KEY, "q": query, "num": min(limit, 10), "engine": "google"},
        timeout=20,
    )
    response.raise_for_status()
    items = response.json().get("organic_results") or []
    return [
        SearchResult(
            url=str(item.get("link", "")),
            title=str(item.get("title", "")),
            snippet=str(item.get("snippet", "")),
            relevance_score=max(50.0, 100.0 - index * 5),
            provider="serpapi",
        )
        for index, item in enumerate(items)
        if item.get("link")
    ]


def _brave_search(query: str, limit: int) -> list[SearchResult]:
    if not settings.BRAVE_SEARCH_API_KEY:
        return []
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": min(limit, 20), "safesearch": "moderate"},
        headers={"Accept": "application/json", "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("web", {}).get("results", []) or []
    return [
        SearchResult(
            url=str(item.get("url", "")),
            title=str(item.get("title", "")),
            snippet=str(item.get("description", "")),
            relevance_score=max(40.0, 100.0 - index * 3),
            provider="brave",
        )
        for index, item in enumerate(items)
        if item.get("url")
    ]


def _fallback_search(query: str, limit: int) -> list[SearchResult]:
    slug = quote_plus(query)
    normalized = query.lower()
    niche = "wellness" if "health" in normalized or "nutrition" in normalized else "creator"
    candidates = [
        SearchResult(
            url=f"https://www.youtube.com/results?search_query={slug}",
            title=f"YouTube creators for {query}",
            snippet=f"Video creators and channel results related to {query}.",
            relevance_score=74,
            provider="fallback",
        ),
        SearchResult(
            url=f"https://www.instagram.com/explore/search/keyword/?q={slug}",
            title=f"Instagram creator search for {query}",
            snippet=f"Public Instagram discovery page for {query}.",
            relevance_score=70,
            provider="fallback",
        ),
        SearchResult(
            url=f"https://medium.com/search?q={slug}",
            title=f"Articles mentioning {query}",
            snippet="Editorial articles that can reveal expert creators, citations, and credentials.",
            relevance_score=66,
            provider="fallback",
        ),
        SearchResult(
            url=f"https://substack.com/search/{slug}",
            title=f"Independent {niche} writers and creators",
            snippet=f"Newsletter profiles and content sources for {query}.",
            relevance_score=62,
            provider="fallback",
        ),
    ]
    return candidates[:limit]


def _search_provider_order() -> list[SearchFn]:
    """Return configured search providers in priority order (failover chain)."""
    mode = settings.SEARCH_PROVIDER_MODE.strip().lower()
    brave = _brave_search
    serpapi = _serp_api_search

    if mode == "brave":
        return [brave, serpapi]
    if mode == "serpapi":
        return [serpapi, brave]
    if mode == "all":
        return [serpapi, brave]

    return [brave, serpapi]


def search_web(query: str, limit: int = 8) -> list[dict]:
    results: list[SearchResult] = []
    mode = settings.SEARCH_PROVIDER_MODE.strip().lower()

    if mode == "all":
        for provider in _search_provider_order():
            try:
                results.extend(provider(query, limit))
            except httpx.HTTPError:
                continue
    else:
        for provider in _search_provider_order():
            try:
                batch = provider(query, limit)
                if batch:
                    results = batch
                    break
            except httpx.HTTPError:
                continue

    if not results:
        results = _fallback_search(query, limit)
    return _dedupe(results, limit)
