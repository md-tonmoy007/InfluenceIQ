from __future__ import annotations

import re

import httpx

from backend.pipeline.content.contracts import compact_number, normalize_url
from backend.pipeline.content.providers.base import PlatformProfile
from backend.pipeline.content.providers.utils import handle_from_url, meta_content


def fetch_x_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url).replace("https://twitter.com/", "https://x.com/")
    handle = handle_from_url(normalized)
    try:
        html = httpx.get(normalized, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text
        description = meta_content(html, "description") or meta_content(html, "og:description")
        title = meta_content(html, "og:title") or handle
        follower_match = re.search(r"([\d.,]+\s*[KMB]?)\s+Followers", html, flags=re.IGNORECASE)
        following_match = re.search(r"([\d.,]+\s*[KMB]?)\s+Following", html, flags=re.IGNORECASE)
        return PlatformProfile(
            platform="x",
            url=normalized,
            handle=handle,
            name=title.replace(" / X", "").replace(" on X", "").strip(),
            bio=description,
            followers=compact_number(follower_match.group(1)) if follower_match else None,
            following=compact_number(following_match.group(1)) if following_match else None,
            verified="is_blue_verified" in html or "Verified account" in html,
            profile_urls=[normalized],
            comments=[description] if description else [],
            provider="x_meta",
        )
    except Exception as exc:
        return PlatformProfile(
            platform="x",
            url=normalized,
            handle=handle,
            name=handle,
            bio="X profile fetch failed; using URL-derived profile identity.",
            profile_urls=[normalized],
            provider="x_fallback",
            error=str(exc),
        )
