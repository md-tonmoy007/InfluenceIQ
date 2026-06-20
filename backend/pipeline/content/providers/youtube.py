from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from backend.pipeline.content.contracts import compact_number, normalize_url
from backend.pipeline.content.providers.base import PlatformProfile
from backend.pipeline.content.providers.utils import handle_from_url, json_ld_blocks, meta_content


def _fetch_html(url: str) -> str:
    response = httpx.get(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
        follow_redirects=True,
        timeout=15,
    )
    response.raise_for_status()
    return response.text


def _channel_id(html: str) -> str:
    for pattern in (
        r'"channelId"\s*:\s*"([^"]+)"',
        r'"externalId"\s*:\s*"([^"]+)"',
        r'<meta itemprop="channelId" content="([^"]+)"',
    ):
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return ""


def _rss_posts(channel_id: str) -> list[dict]:
    if not channel_id:
        return []
    response = httpx.get(
        "https://www.youtube.com/feeds/videos.xml",
        params={"channel_id": channel_id},
        timeout=15,
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    posts = []
    for entry in root.findall("atom:entry", ns)[:12]:
        posts.append({
            "id": (entry.findtext("yt:videoId", default="", namespaces=ns) or ""),
            "title": (entry.findtext("atom:title", default="", namespaces=ns) or ""),
            "url": (entry.findtext("atom:link", default="", namespaces=ns) or ""),
            "published_at": (entry.findtext("atom:published", default="", namespaces=ns) or ""),
            "description": (entry.findtext("media:group/media:description", default="", namespaces=ns) or ""),
        })
    return posts


def fetch_youtube_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url)
    handle = handle_from_url(normalized)
    try:
        html = _fetch_html(normalized)
        description = meta_content(html, "description") or meta_content(html, "og:description")
        title = meta_content(html, "og:title") or handle
        channel_id = _channel_id(html)
        subscribers = compact_number(description)
        if subscribers is None:
            sub_match = re.search(r"([\d.,]+\s*[KMB]?)\s+subscribers", html, flags=re.IGNORECASE)
            subscribers = compact_number(sub_match.group(1)) if sub_match else None
        posts = _rss_posts(channel_id)
        for block in json_ld_blocks(html):
            title = title or str(block.get("name") or "")
            description = description or str(block.get("description") or "")
        comments = [
            post["description"][:220]
            for post in posts
            if post.get("description")
        ][:20]
        return PlatformProfile(
            platform="youtube",
            url=normalized,
            handle=handle,
            name=title.replace(" - YouTube", "").strip(),
            bio=description,
            followers=subscribers,
            verified="Verified" in html or '"BADGE_STYLE_TYPE_VERIFIED"' in html,
            profile_urls=[normalized],
            posts=posts,
            comments=comments,
            raw={"channel_id": channel_id},
            provider="youtube",
        )
    except Exception as exc:
        return PlatformProfile(
            platform="youtube",
            url=normalized,
            handle=handle,
            name=handle,
            bio="YouTube profile fetch failed; using URL-derived profile identity.",
            profile_urls=[normalized],
            provider="youtube_fallback",
            error=str(exc),
        )
