from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from urllib.parse import quote, urlparse

import httpx
import redis
from celery import shared_task

from app.config import settings
from app.services.crawl_policy import is_social_domain, select_discovered_links
from app.services.pipeline_state import emit_event, update_state

_META_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?P<key>[^"\']+)["\'][^>]+content=["\'](?P<value>[^"\']*)["\'][^>]*>',
    flags=re.IGNORECASE,
)
_BOT_BLOCK_MARKERS = (
    "captcha",
    "access denied",
    "please verify you are human",
    "unusual traffic",
    "temporarily blocked",
)


@lru_cache(maxsize=1)
def _cache_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_STATE_DB)


def _cache_key(url: str) -> str:
    return f"url_cache:{hashlib.sha256(url.encode('utf-8')).hexdigest()}"


def _rate_limit_key(domain: str) -> str:
    return f"rate_limit:{domain}"


def _sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _utc_timestamp() -> float:
    return time.time()


def _strip_html(html: str) -> str:
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_html(html: str, url: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _strip_html(match.group(1))
    return url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()


def _social_links_from_html(html: str) -> list[str]:
    direct_links = re.findall(r"https?://(?:www\.)?(?:instagram|youtube|tiktok|linkedin)\.com/[^\s\"'<>]+", html)
    handles = [f"https://instagram.com/{handle}" for handle in re.findall(r"@([A-Za-z0-9_.]{3,30})", html)]
    return sorted(set(direct_links + handles))


def _metadata_from_html(html: str, url: str, page: dict) -> dict:
    metadata = {
        "status": page.get("status"),
        "cached": bool(page.get("cached", False)),
        "fetched_at": page.get("fetched_at"),
        "domain": urlparse(url).netloc,
    }
    for match in _META_RE.finditer(html):
        key = str(match.group("key") or "").strip().lower()
        value = str(match.group("value") or "").strip()
        if key in {"author", "article:author", "og:title", "og:description", "description", "article:published_time"} and value:
            metadata[key.replace(":", "_")] = value
    return metadata


def _coerce_fetch_result(value: Any, provider: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "html": str(value.get("html") or ""),
            "status": int(value.get("status") or 200),
            "provider": str(value.get("provider") or provider),
        }
    return {"html": str(value or ""), "status": 200, "provider": provider}


def _fetch_via_scrape_do(url: str) -> dict[str, Any]:
    params = {
        "token": settings.SCRAPE_DO_API_KEY,
        "url": url,
        "render": "true",
        "super": "true",
    }
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(settings.SCRAPE_DO_BASE_URL, params=params)
        return {"html": response.text, "status": response.status_code, "provider": "scrape.do"}


def _archive_url(url: str) -> str:
    return f"https://web.archive.org/web/*/{quote(url, safe='')}"


def _should_retry(status: int, html: str, error: Exception | None = None) -> bool:
    if error is not None:
        return isinstance(error, httpx.TimeoutException | httpx.HTTPError)
    if status in {403, 429, 500, 502, 503, 504}:
        return True
    lowered = (html or "").casefold()
    return any(marker in lowered for marker in _BOT_BLOCK_MARKERS)


def _retry_delay(attempt: int) -> float:
    return min(settings.CRAWL_BACKOFF_SECONDS * (2 ** max(0, attempt - 1)), settings.CRAWL_BACKOFF_MAX_SECONDS)


def _domain_interval(domain: str) -> float:
    if is_social_domain(f"https://{domain}"):
        return float(settings.CRAWL_SOCIAL_MIN_INTERVAL_SECONDS)
    return float(settings.CRAWL_DEFAULT_MIN_INTERVAL_SECONDS)


def _apply_domain_throttle(domain: str) -> float:
    client = _cache_redis()
    key = _rate_limit_key(domain)
    interval = _domain_interval(domain)
    now = _utc_timestamp()
    last_seen = client.get(key)
    last = float(last_seen.decode("utf-8") if isinstance(last_seen, bytes) else last_seen or "0")
    wait_for = max(0.0, interval - (now - last))
    if wait_for <= 0:
        client.setex(key, max(1, int(interval * 10)), str(now))
    return round(wait_for, 3)


def _fetch_with_resilience(campaign_id: str, url: str, domain: str) -> dict[str, Any]:
    if not settings.SCRAPE_DO_API_KEY:
        return {
            "html": (
                "<html><head><title>Demo creator profile</title></head><body>"
                "<h1>Dr Sarah Tan</h1>"
                "<p>Certified nutrition educator with Instagram @drsarahtan and YouTube creator presence.</p>"
                "<p>Known for evidence-based wellness content and positive brand collaborations.</p>"
                "</body></html>"
            ),
            "status": 200,
            "provider": "deterministic",
            "attempt_count": 1,
            "archive_fallback_used": False,
            "rate_limited": False,
        }

    attempt = 0
    rate_limited = False
    while attempt < settings.CRAWL_MAX_RETRIES:
        attempt += 1
        wait_for = _apply_domain_throttle(domain)
        if wait_for > 0:
            rate_limited = True
            emit_event(campaign_id, "page.rate_limited", {"url": url, "domain": domain, "wait_seconds": wait_for})
            _sleep(wait_for)
        try:
            result = _coerce_fetch_result(_fetch_via_scrape_do(url), "scrape.do")
            if not _should_retry(int(result["status"]), str(result["html"])):
                return {
                    **result,
                    "attempt_count": attempt,
                    "archive_fallback_used": False,
                    "rate_limited": rate_limited,
                }
        except httpx.HTTPError as exc:
            result = {"html": "", "status": 599, "provider": "scrape.do"}
            if not _should_retry(599, "", exc):
                raise

        if attempt < settings.CRAWL_MAX_RETRIES:
            delay = _retry_delay(attempt)
            emit_event(
                campaign_id,
                "page.retry_scheduled",
                {"url": url, "domain": domain, "attempt": attempt + 1, "delay_seconds": delay},
            )
            _sleep(delay)

    archive_target = _archive_url(url)
    emit_event(campaign_id, "page.archive_fallback", {"url": url, "archive_url": archive_target})
    archive = _coerce_fetch_result(_fetch_via_scrape_do(archive_target), "scrape.do")
    return {
        **archive,
        "attempt_count": settings.CRAWL_MAX_RETRIES + 1,
        "archive_fallback_used": True,
        "rate_limited": rate_limited,
    }


@shared_task(name="app.tasks.crawl.fetch_page", bind=True)
def fetch_page(
    self,
    campaign_id: str,
    url: str,
    *,
    depth: int = 1,
    source_type: str = "search_result",
    parent_url: str = "",
) -> dict:
    """URL cache check -> live fetch -> store.
    Returns {url, html, status, cached: bool, fetched_at}."""
    fetched_at = datetime.now(UTC).isoformat()
    cache_key = _cache_key(url)
    domain = urlparse(url).netloc.casefold()

    try:
        cached_payload = _cache_redis().get(cache_key)
    except redis.RedisError:
        cached_payload = None

    if cached_payload:
        if isinstance(cached_payload, bytes):
            cached_payload = cached_payload.decode("utf-8")
        page = json.loads(str(cached_payload))
        page["cached"] = True
        page.setdefault("provider", "cache")
        page.setdefault("attempt_count", 0)
        page.setdefault("archive_fallback_used", False)
        page.setdefault("domain", domain)
        page.setdefault("rate_limited", False)
        page["depth"] = depth
        page["source_type"] = source_type
        page["parent_url"] = parent_url
        update_state(campaign_id, phase="crawl", last_url=url, last_status=page.get("status", 200))
        emit_event(campaign_id, "url.cache_hit", {"url": url})
        return page

    fetch_result = _fetch_with_resilience(campaign_id, url, domain)
    page = {
        "url": url,
        "html": fetch_result["html"],
        "status": fetch_result["status"],
        "cached": False,
        "fetched_at": fetched_at,
        "provider": fetch_result["provider"],
        "attempt_count": fetch_result["attempt_count"],
        "archive_fallback_used": fetch_result["archive_fallback_used"],
        "domain": domain,
        "rate_limited": fetch_result["rate_limited"],
        "depth": depth,
        "source_type": source_type,
        "parent_url": parent_url,
    }
    try:
        _cache_redis().setex(cache_key, settings.URL_CACHE_TTL_SECONDS, json.dumps(page))
    except redis.RedisError:
        pass

    update_state(
        campaign_id,
        phase="crawl",
        last_url=url,
        last_status=page["status"],
        crawl_provider=page["provider"],
    )
    emit_event(
        campaign_id,
        "page.scraped",
        {
            "url": url,
            "status": page["status"],
            "provider": page["provider"],
            "attempt_count": page["attempt_count"],
            "archive_fallback_used": page["archive_fallback_used"],
        },
    )
    return page


@shared_task(name="app.tasks.crawl.extract_content", bind=True)
def extract_content(self, page: dict) -> dict:
    """HTML cleanup + metadata + social link discovery.
    Returns {url, title, content, social_links[], metadata}."""
    url = page.get("url", "")
    html = page.get("html", "")
    content = {
        "url": url,
        "title": _title_from_html(html, url),
        "content": _strip_html(html),
        "social_links": _social_links_from_html(html),
        "discovered_links": select_discovered_links(
            html,
            url,
            depth=int(page.get("depth") or 1),
            max_depth=settings.CRAWL_MAX_DEPTH,
        ),
        "metadata": _metadata_from_html(html, url, page),
    }
    return content
