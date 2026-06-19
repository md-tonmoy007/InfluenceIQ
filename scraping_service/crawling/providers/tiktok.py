from __future__ import annotations

import re

import httpx

from scraping_service.crawling.contracts import compact_number, normalize_url
from scraping_service.crawling.providers.base import PlatformProfile
from scraping_service.crawling.providers.utils import handle_from_url, meta_content


def fetch_tiktok_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url)
    handle = handle_from_url(normalized)
    if not handle and "/@" in normalized:
        handle = normalized.split("/@", 1)[1].split("/", 1)[0]
    handle = handle.lstrip("@")
    try:
        html = httpx.get(normalized, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text
        description = meta_content(html, "description") or meta_content(html, "og:description")
        title = meta_content(html, "og:title") or handle
        follower_match = re.search(r"([\d.,]+\s*[KMB]?)\s+Followers", html, flags=re.IGNORECASE)
        likes_match = re.search(r"([\d.,]+\s*[KMB]?)\s+Likes", html, flags=re.IGNORECASE)
        followers = compact_number(follower_match.group(1)) if follower_match else compact_number(description)
        likes = compact_number(likes_match.group(1)) if likes_match else None
        return PlatformProfile(
            platform="tiktok",
            url=normalized,
            handle=handle,
            name=title.replace("| TikTok", "").strip(),
            bio=description,
            followers=followers,
            average_engagement=likes,
            verified="verified" in html.lower(),
            profile_urls=[normalized],
            comments=[description] if description else [],
            provider="tiktok_meta",
        )
    except Exception as exc:
        return PlatformProfile(
            platform="tiktok",
            url=normalized,
            handle=handle,
            name=handle,
            bio="TikTok profile fetch failed; using URL-derived profile identity.",
            profile_urls=[normalized],
            provider="tiktok_fallback",
            error=str(exc),
        )
