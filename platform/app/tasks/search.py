from __future__ import annotations

import json
import re
import uuid
from html import unescape
from urllib.parse import quote_plus, urlparse

import httpx
from celery import shared_task

from app.config import settings
from app.db import SessionLocal
from app.llm.client import LLMRequest, complete_or_fallback
from app.models import Campaign
from app.services.pipeline_state import emit_event, update_state

QUERY_PROMPT_PATH = "platform/app/llm/prompts/query_generation.md"
_RESULT_LINK_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
    flags=re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", _TAG_RE.sub(" ", unescape(value))).strip()


def _prompt_template() -> str:
    with open(QUERY_PROMPT_PATH, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def _campaign_context(campaign_id: str) -> dict:
    session = SessionLocal()
    try:
        campaign = session.get(Campaign, uuid.UUID(campaign_id))
        if campaign is None:
            return {"campaign_id": campaign_id}
        payload = dict(campaign.payload or {})
        return {
            "campaign_id": campaign_id,
            "brand": campaign.brand,
            "product": campaign.product,
            "category": campaign.category,
            "goal": campaign.goal,
            "platforms": payload.get("platforms", []),
            "locations": payload.get("locations", []),
            "ages": payload.get("ages", []),
            "gender": payload.get("gender", ""),
            "tier": payload.get("tier", ""),
            "budget": payload.get("budget", ""),
            "notes": payload.get("notes", ""),
            "query": payload.get("query", ""),
        }
    finally:
        session.close()


def _topic_from_context(context: dict) -> str:
    freeform_query = str(context.get("query") or "").strip()
    if freeform_query:
        return freeform_query

    parts = [
        str(context.get("brand") or "").strip(),
        str(context.get("product") or "").strip(),
        str(context.get("category") or "").strip(),
        str(context.get("goal") or "").strip(),
        str(context.get("notes") or "").strip(),
    ]
    topic = " ".join(part for part in parts if part).strip()
    if topic:
        return topic
    cleaned = str(context.get("campaign_id") or "").replace("-", " ").replace("_", " ").strip()
    if not cleaned or cleaned.lower() in {"demo", "test"}:
        return "health and wellness creators"
    return cleaned


def _fallback_queries(context: dict) -> list[str]:
    topic = _topic_from_context(context)
    requested_platforms = [str(platform).strip() for platform in (context.get("platforms") or []) if str(platform).strip()]
    base_queries = [
        f"{topic} influencers",
        f"{topic} creators",
        f"{topic} brand safe creators",
        f"{topic} certified professionals social media",
    ]
    for platform in requested_platforms[:3]:
        base_queries.append(f"{topic} {platform} creators")
    if not requested_platforms:
        base_queries.extend(
            [
                f"{topic} Instagram creators",
                f"{topic} YouTube experts",
            ]
        )
    return list(dict.fromkeys(query for query in base_queries if query.strip()))[:8]


def _query_prompt(context: dict) -> str:
    campaign_json = json.dumps(context, indent=2, sort_keys=True)
    return (
        f"{_prompt_template()}\n\n"
        "Return a JSON object with one key named `queries` containing 6 to 8 unique search queries.\n"
        "The queries should target real web discovery of credible creators, domain experts, interviews, and social profiles.\n"
        "Prefer high-intent queries with platform names, professional credentials, niche keywords, and brand-safety hints when relevant.\n\n"
        f"Campaign brief:\n{campaign_json}\n"
    )


def _normalize_queries(raw_text: str, fallback_queries: list[str]) -> list[str]:
    try:
        payload = json.loads(raw_text)
        values = payload.get("queries", payload if isinstance(payload, list) else [])
        if isinstance(values, list):
            queries = [str(value).strip() for value in values if str(value).strip()]
            if queries:
                return list(dict.fromkeys(queries))[:8]
    except json.JSONDecodeError:
        pass

    extracted = [
        line.strip(" -\t\r\n0123456789.")
        for line in raw_text.splitlines()
        if line.strip()
    ]
    queries = [line for line in extracted if line]
    return list(dict.fromkeys(queries or fallback_queries))[:8]


def _search_via_brave(query: str) -> list[dict]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY},
            params={"q": query, "count": min(settings.SEARCH_RESULT_LIMIT, 20), "safesearch": "moderate"},
        )
        response.raise_for_status()
        body = response.json()

    results: list[dict] = []
    for item in (body.get("web") or {}).get("results", []):
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        results.append(
            {
                "url": url,
                "title": str(item.get("title") or url),
                "snippet": str(item.get("description") or ""),
                "relevance_score": 80,
                "source": "brave",
            }
        )
    return results[: settings.SEARCH_RESULT_LIMIT]


def _search_via_serp_api(query: str) -> list[dict]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "api_key": settings.SERP_API_KEY,
                "num": settings.SEARCH_RESULT_LIMIT,
            },
        )
        response.raise_for_status()
        body = response.json()

    results: list[dict] = []
    for item in body.get("organic_results", []):
        url = str(item.get("link") or "").strip()
        if not url:
            continue
        results.append(
            {
                "url": url,
                "title": str(item.get("title") or url),
                "snippet": str(item.get("snippet") or ""),
                "relevance_score": 80,
                "source": "serpapi",
            }
        )
    return results[: settings.SEARCH_RESULT_LIMIT]


def _fetch_via_scrape_do(target_url: str, *, render: bool = False) -> str:
    params = {
        "token": settings.SCRAPE_DO_API_KEY,
        "url": target_url,
        "render": str(render).lower(),
    }
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(settings.SCRAPE_DO_BASE_URL, params=params)
        response.raise_for_status()
        return response.text


def _search_via_scrape_do(query: str) -> list[dict]:
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html = _fetch_via_scrape_do(search_url, render=False)
    results: list[dict] = []
    for match in _RESULT_LINK_RE.finditer(html):
        url = unescape(match.group("href")).strip()
        title = _strip_html(match.group("title"))
        if not url or not title:
            continue
        host = urlparse(url).netloc
        results.append(
            {
                "url": url,
                "title": title,
                "snippet": f"Search result from {host}" if host else "",
                "relevance_score": 72,
                "source": "scrape.do",
            }
        )
        if len(results) >= settings.SEARCH_RESULT_LIMIT:
            break
    return results


@shared_task(name="app.tasks.search.generate_queries", bind=True)
def generate_queries(self, campaign_id: str) -> list[str]:
    context = _campaign_context(campaign_id)
    fallback_queries = _fallback_queries(context)
    response = complete_or_fallback(
        LLMRequest(
            task_type="generate_queries",
            prompt=_query_prompt(context),
            max_tokens=min(settings.TOKEN_BUDGET_QUERY_GEN, 600),
        ),
        fallback_text=json.dumps({"queries": fallback_queries}),
    )
    queries = _normalize_queries(response.text, fallback_queries)
    update_state(
        campaign_id,
        phase="search",
        generated_query_count=len(queries),
        query_generation_provider=response.provider,
        query_generation_model=response.model,
        query_generation_fallback=response.fallback,
    )
    emit_event(
        campaign_id,
        "query.generated",
        {
            "queries": queries,
            "provider": response.provider,
            "model": response.model,
            "fallback": response.fallback,
        },
    )
    return queries


@shared_task(name="app.tasks.search.execute_search", bind=True)
def execute_search(self, campaign_id: str, query: str) -> list[dict]:
    results: list[dict]
    provider = "serpapi"
    try:
        if settings.SERP_API_KEY:
            results = _search_via_serp_api(query)
        elif settings.BRAVE_SEARCH_API_KEY:
            provider = "brave"
            results = _search_via_brave(query)
        elif settings.SCRAPE_DO_API_KEY:
            provider = "scrape.do"
            results = _search_via_scrape_do(query)
        else:
            slug = quote_plus(query.lower())
            provider = "deterministic"
            results = [
                {
                    "url": f"https://example.com/influencers/{slug}",
                    "title": f"Top creators for {query}",
                    "snippet": f"Fallback search result for {query}.",
                    "relevance_score": 60,
                    "source": provider,
                }
            ]
    except (httpx.HTTPError, ValueError):
        slug = quote_plus(query.lower())
        provider = "deterministic"
        results = [
            {
                "url": f"https://example.com/influencers/{slug}",
                "title": f"Fallback creators for {query}",
                "snippet": f"Fallback search result for {query}.",
                "relevance_score": 60,
                "source": provider,
            }
        ]

    update_state(
        campaign_id,
        phase="search",
        last_query=query,
        discovered_url_count=len(results),
        search_provider=provider,
    )
    for result in results:
        emit_event(
            campaign_id,
            "url.discovered",
            {
                "url": result["url"],
                "title": result["title"],
                "relevance": result["relevance_score"],
                "provider": provider,
            },
        )
    return results
