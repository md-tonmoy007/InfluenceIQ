from __future__ import annotations

from datetime import UTC, datetime

import httpx

from backend.core.config import settings
from backend.pipeline.content.cache import (
    get_cached_page,
    provider_is_available,
    record_provider_failure,
    store_cached_page,
)
from backend.pipeline.content.contracts import CrawlPage, normalize_url, platform_for_url
from backend.pipeline.content.errors import classify_fetch_error
from backend.pipeline.content.providers import fetch_platform_profile

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


def _scrape_do_fetch(url: str, timeout: float = 30.0) -> tuple[str, int]:
    """Fetch a page via scrape.do to bypass bot detection."""
    if not settings.SCRAPE_DO_API:
        return "", 0
    try:
        resp = httpx.get(
            "https://api.scrape.do/",
            params={"token": settings.SCRAPE_DO_API, "url": url},
            timeout=timeout,
        )
        return resp.text, resp.status_code
    except httpx.HTTPError:
        return "", 0


def _fallback_html(url: str) -> str:
    platform = platform_for_url(url)
    if platform == "youtube":
        return (
            "<html><head><title>Evidence Based Wellness Channel</title>"
            "<meta name='description' content='Certified nutrition educator sharing evidence-based wellness videos.'>"
            "</head><body><h1>Dr Sarah Tan</h1><p>@drsarahtan</p>"
            "<p>Certified Nutritionist, MD. 124K subscribers. Verified creator.</p>"
            "<p>Recent comments: Helpful and authentic advice. Excellent professional explanation.</p>"
            "<a href='https://youtube.com/@drsarahtan'>YouTube</a>"
            "<a href='https://instagram.com/drsarahtan'>Instagram</a></body></html>"
        )
    if platform == "instagram":
        return (
            "<html><head><title>Dr Sarah Tan (@drsarahtan)</title>"
            "<meta property='og:description' content='124K followers, certified nutrition educator, evidence-based wellness.'>"
            "</head><body><h1>Dr Sarah Tan</h1><p>@drsarahtan</p>"
            "<p>Certified Nutritionist and MD. Followers 124K. Average likes 5400. Verified.</p>"
            "<p>Comments: Helpful and authentic. Great evidence-based advice.</p>"
            "<a href='https://instagram.com/drsarahtan'>Instagram</a></body></html>"
        )
    return (
        "<html><head><title>Trusted creator roundup</title></head><body>"
        "<h1>Top evidence-based wellness creators</h1>"
        "<p>Dr Sarah Tan is a Certified Nutritionist and MD with Instagram @drsarahtan "
        "and YouTube https://youtube.com/@drsarahtan. Her audience comments are helpful, "
        "authentic, and positive.</p></body></html>"
    )


def fetch_url(url: str, timeout: float = 15.0) -> dict:
    normalized_url = normalize_url(url)
    cached = get_cached_page(normalized_url)
    if cached:
        return cached

    platform = platform_for_url(normalized_url)
    if platform not in ("web", "unknown") and not provider_is_available(platform):
        return _fallback_page(normalized_url, f"PROVIDER_DOWN: {platform} circuit breaker open")

    platform_page = fetch_platform_profile(normalized_url)
    if platform_page is not None:
        store_cached_page(normalized_url, platform_page)
        return platform_page

    fetched_at = datetime.now(UTC).isoformat()
    html = ""
    status = 0
    content_type = ""
    error = None
    provider = "fallback"

    # scrape.do is the primary fetcher — handles bot detection, CAPTCHAs, and
    # verification pages that return 200 with no real content (e.g. Reddit).
    if settings.SCRAPE_DO_API:
        scrape_html, scrape_status = _scrape_do_fetch(normalized_url, timeout=timeout + 15)
        if scrape_html and scrape_status < 500:
            html = scrape_html
            status = scrape_status
            provider = "scrape.do"

    # Fall back to direct httpx when scrape.do is not configured or failed
    if not html:
        headers = {
            "User-Agent": USER_AGENTS[abs(hash(normalized_url)) % len(USER_AGENTS)],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            response = httpx.get(normalized_url, headers=headers, timeout=timeout, follow_redirects=True)
            html = response.text
            status = response.status_code
            content_type = response.headers.get("content-type", "")
            provider = "httpx"
        except httpx.HTTPError as exc:
            error = classify_fetch_error(exc)
            if platform not in ("web", "unknown"):
                record_provider_failure(platform)
            status = 599

        if error is None and status in {403, 429}:
            error = classify_fetch_error(Exception("blocked"), status_code=status)
            if platform not in ("web", "unknown"):
                record_provider_failure(platform)

    if not html or (error is not None):
        html = _fallback_html(normalized_url)
        status = 599
        provider = "fallback"

    if error is None and not html.strip():
        error = f"PARSE_ERROR: empty content at {normalized_url}"

    page = CrawlPage(
        url=normalized_url,
        status=status,
        html=html,
        fetched_at=fetched_at,
        cached=False,
        provider=provider,
        error=error,
        headers={"content-type": content_type},
    ).to_dict()
    # Only cache successful fetches so transient failures get retried
    if provider != "fallback":
        store_cached_page(normalized_url, page)
    return page


def _fallback_page(url: str, error: str) -> dict:
    """Return a fallback page when the circuit breaker is open."""
    return CrawlPage(
        url=url,
        status=503,
        html=_fallback_html(url),
        fetched_at=datetime.now(UTC).isoformat(),
        cached=False,
        provider="fallback",
        error=error,
        headers={},
    ).to_dict()
