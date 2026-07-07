from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import httpx

from backend.core.config import settings
from backend.pipeline.content.contracts import compact_number, normalize_url
from backend.pipeline.content.providers.base import PlatformProfile
from backend.pipeline.content.providers.utils import handle_from_url, json_ld_blocks, meta_content

log = logging.getLogger(__name__)


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


def _channels_api_fetch(channel_id: str) -> dict | None:
    if not settings.YOUTUBE_API_KEY or not channel_id:
        return None
    try:
        response = httpx.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "id": channel_id,
                "part": "statistics,snippet,brandingSettings",
            },
            timeout=15,
        )
        response.raise_for_status()
        items = response.json().get("items") or []
        if not items:
            return None
        return items[0]
    except Exception as exc:
        log.debug("_channels_api_fetch failed for %s: %s", channel_id, exc)
        return None


def _videos_api_fetch(video_ids: list[str]) -> dict[str, dict]:
    if not settings.YOUTUBE_API_KEY or not video_ids:
        return {}
    try:
        response = httpx.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "id": ",".join(video_ids),
                "part": "statistics,snippet",
            },
            timeout=15,
        )
        response.raise_for_status()
        items = response.json().get("items") or []
        return {item["id"]: item for item in items if isinstance(item, dict) and "id" in item}
    except Exception as exc:
        log.debug("_videos_api_fetch failed: %s", exc)
        return {}


def _stats_or_none(stats: dict, key: str) -> int | None:
    try:
        val = stats.get(key)
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def fetch_youtube_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url)
    handle = handle_from_url(normalized)
    try:
        html = _fetch_html(normalized)
        description = meta_content(html, "description") or meta_content(html, "og:description")
        title = meta_content(html, "og:title") or handle
        channel_id = _channel_id(html)
        posts = _rss_posts(channel_id)
        for block in json_ld_blocks(html):
            title = title or str(block.get("name") or "")
            description = description or str(block.get("description") or "")

        if settings.YOUTUBE_API_KEY and channel_id:
            channel_raw = _channels_api_fetch(channel_id)
            if channel_raw is not None:
                stats = (channel_raw.get("statistics") or {}) if isinstance(channel_raw, dict) else {}
                snippet = (channel_raw.get("snippet") or {}) if isinstance(channel_raw, dict) else {}
                api_title = str(snippet.get("title") or "").replace(" - YouTube", "").strip()
                api_description = str(snippet.get("description") or "")
                title = api_title or title
                description = api_description or description
                subscribers = _stats_or_none(stats, "subscriberCount")
                lifetime_views = _stats_or_none(stats, "viewCount")
                video_count = _stats_or_none(stats, "videoCount")
                verified = bool(
                    snippet.get("customUrl")
                    and (channel_raw.get("status") or {}).get("isLinked")
                )

                video_ids = [p["id"] for p in posts if p.get("id")]
                if video_ids:
                    video_stats_map = _videos_api_fetch(video_ids)
                    for post in posts:
                        vid = post.get("id")
                        vs = video_stats_map.get(vid, {})
                        vs_stats = (vs.get("statistics") or {}) if isinstance(vs, dict) else {}
                        post["view_count"] = _stats_or_none(vs_stats, "viewCount")
                        post["like_count"] = _stats_or_none(vs_stats, "likeCount")
                        post["comment_count"] = _stats_or_none(vs_stats, "commentCount")
                raw = {
                    "channel_id": channel_id,
                    "lifetime_views": lifetime_views,
                    "video_count": video_count,
                    "api_source": "youtube_data_v3",
                }
                return PlatformProfile(
                    platform="youtube",
                    url=normalized,
                    handle=handle,
                    name=title,
                    bio=description,
                    followers=subscribers,
                    verified=verified,
                    profile_urls=[normalized],
                    posts=posts,
                    comments=[
                        post["description"][:220]
                        for post in posts
                        if post.get("description")
                    ][:20],
                    raw=raw,
                    provider="youtube",
                )

        subscribers = compact_number(description)
        if subscribers is None:
            sub_match = re.search(r"([\d.,]+\s*[KMB]?)\s+subscribers", html, flags=re.IGNORECASE)
            subscribers = compact_number(sub_match.group(1)) if sub_match else None
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
            provider="youtube_html_fallback" if settings.YOUTUBE_API_KEY else "youtube",
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
