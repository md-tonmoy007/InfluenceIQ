from __future__ import annotations

from urllib.parse import quote_plus

import httpx

from backend.core.config import settings
from backend.pipeline.content.contracts import SearchResult


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


def _openserp_search(query: str, limit: int) -> list[SearchResult]:
    if not settings.OPENSERP_URL:
        return []
    headers = {"Authorization": f"Bearer {settings.OPENSERP_API_KEY}"} if settings.OPENSERP_API_KEY else {}
    response = httpx.get(
        settings.OPENSERP_URL.rstrip("/"),
        params={"q": query, "num": limit},
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("organic_results") or payload.get("results") or []
    return [
        SearchResult(
            url=str(item.get("link") or item.get("url") or ""),
            title=str(item.get("title", "")),
            snippet=str(item.get("snippet") or item.get("description") or ""),
            relevance_score=max(35.0, 90.0 - index * 4),
            provider="openserp",
        )
        for index, item in enumerate(items)
        if item.get("link") or item.get("url")
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


def search_web(query: str, limit: int = 8) -> list[dict]:
    results: list[SearchResult] = []
    for provider in (_serp_api_search, _brave_search, _openserp_search):
        try:
            results.extend(provider(query, limit))
        except httpx.HTTPError:
            continue
    if not results:
        results = _fallback_search(query, limit)
    return _dedupe(results, limit)
