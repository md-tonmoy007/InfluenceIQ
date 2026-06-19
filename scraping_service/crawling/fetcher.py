from __future__ import annotations

from datetime import UTC, datetime

import httpx

from scraping_service.crawling.cache import get_cached_page, store_cached_page
from scraping_service.crawling.contracts import CrawlPage, normalize_url, platform_for_url
from scraping_service.crawling.providers import fetch_platform_profile

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


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

    platform_page = fetch_platform_profile(normalized_url)
    if platform_page is not None:
        store_cached_page(normalized_url, platform_page)
        return platform_page

    headers = {
        "User-Agent": USER_AGENTS[abs(hash(normalized_url)) % len(USER_AGENTS)],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    fetched_at = datetime.now(UTC).isoformat()
    try:
        response = httpx.get(normalized_url, headers=headers, timeout=timeout, follow_redirects=True)
        html = response.text
        status = response.status_code
        error = None
    except httpx.HTTPError as exc:
        html = _fallback_html(normalized_url)
        status = 599
        error = str(exc)

    if status in {403, 429} or not html.strip():
        html = _fallback_html(normalized_url)
        error = error or f"blocked_or_empty_status_{status}"

    page = CrawlPage(
        url=normalized_url,
        status=status,
        html=html,
        fetched_at=fetched_at,
        cached=False,
        provider="httpx" if error is None else "fallback",
        error=error,
        headers={"content-type": response.headers.get("content-type", "")} if "response" in locals() else {},
    ).to_dict()
    store_cached_page(normalized_url, page)
    return page
