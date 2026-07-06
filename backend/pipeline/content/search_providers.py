from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote_plus

import httpx

from backend.core.config import settings
from backend.pipeline.content.contracts import SearchResult

SearchFn = Callable[[str, int, "str | None"], list[SearchResult]]

# Common campaign target markets -> ISO 3166-1 alpha-2 code. Used to bias
# SerpApi (`gl`) / Brave (`country`) results toward the campaign's target
# location, on top of the location already being embedded in the query text.
# Not exhaustive — unmapped locations simply skip the country param and rely
# on the query text alone.
_COUNTRY_CODES: dict[str, str] = {
    "india": "in",
    "united states": "us",
    "usa": "us",
    "us": "us",
    "united kingdom": "gb",
    "uk": "gb",
    "singapore": "sg",
    "malaysia": "my",
    "indonesia": "id",
    "philippines": "ph",
    "vietnam": "vn",
    "thailand": "th",
    "australia": "au",
    "canada": "ca",
    "uae": "ae",
    "united arab emirates": "ae",
    "saudi arabia": "sa",
    "nigeria": "ng",
    "south africa": "za",
    "brazil": "br",
    "mexico": "mx",
    "germany": "de",
    "france": "fr",
    "spain": "es",
    "italy": "it",
    "japan": "jp",
    "south korea": "kr",
    "china": "cn",
    "pakistan": "pk",
    "bangladesh": "bd",
}


def _country_code(location: str | None) -> str | None:
    """Best-effort ISO country code for a free-text location string."""
    if not location:
        return None
    normalized = location.strip().lower()
    if normalized in _COUNTRY_CODES:
        return _COUNTRY_CODES[normalized]
    for name, code in _COUNTRY_CODES.items():
        if name in normalized:
            return code
    return None


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


def _serp_api_search(query: str, limit: int, location: str | None = None) -> list[SearchResult]:
    if not settings.SERP_API_KEY:
        return []
    params: dict[str, Any] = {
        "api_key": settings.SERP_API_KEY, "q": query, "num": min(limit, 10), "engine": "google",
    }
    if location:
        params["location"] = location
    country = _country_code(location)
    if country:
        params["gl"] = country
    response = httpx.get(
        "https://serpapi.com/search.json",
        params=params,
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


def _brave_search(query: str, limit: int, location: str | None = None) -> list[SearchResult]:
    if not settings.BRAVE_SEARCH_API_KEY:
        return []
    params: dict[str, Any] = {"q": query, "count": min(limit, 20), "safesearch": "moderate"}
    country = _country_code(location)
    if country:
        params["country"] = country.upper()
    response = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params=params,
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


def _fallback_search(query: str, limit: int, location: str | None = None) -> list[SearchResult]:
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


def search_web(query: str, limit: int = 8, location: str | None = None) -> list[dict]:
    results: list[SearchResult] = []
    mode = settings.SEARCH_PROVIDER_MODE.strip().lower()

    if mode == "all":
        for provider in _search_provider_order():
            try:
                results.extend(provider(query, limit, location))
            except httpx.HTTPError:
                continue
    else:
        for provider in _search_provider_order():
            try:
                batch = provider(query, limit, location)
                if batch:
                    results = batch
                    break
            except httpx.HTTPError:
                continue

    if not results:
        results = _fallback_search(query, limit, location)
    return _dedupe(results, limit)
