from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import httpx

from backend.core.config import settings
from backend.pipeline.content.cache import (
    YOUTUBE_RSS_CACHE_TTL,
    get_cached_youtube_api,
    store_cached_youtube_api,
)
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

    cached = get_cached_youtube_api("rss", channel_id)
    if cached is not None:
        return [post for post in cached if isinstance(post, dict)]

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
        link_el = entry.find("atom:link", ns)
        link_url = (link_el.get("href") if link_el is not None else "") or ""
        posts.append({
            "id": (entry.findtext("yt:videoId", default="", namespaces=ns) or ""),
            "title": (entry.findtext("atom:title", default="", namespaces=ns) or ""),
            "url": link_url,
            "published_at": (entry.findtext("atom:published", default="", namespaces=ns) or ""),
            "description": (entry.findtext("media:group/media:description", default="", namespaces=ns) or ""),
        })
    store_cached_youtube_api("rss", channel_id, posts, ttl=YOUTUBE_RSS_CACHE_TTL)
    return posts


def _channels_api_fetch(channel_id: str = "", handle: str = "") -> dict | None:
    if not settings.YOUTUBE_API_KEY:
        return None
    if not channel_id and not handle:
        return None
    use_handle = bool(handle)
    cache_kind = "handle" if use_handle else "id"
    cache_value = (handle if handle.startswith("@") else f"@{handle}") if use_handle else channel_id

    cached = get_cached_youtube_api(cache_kind, cache_value)
    if cached is not None:
        items = cached.get("items") or []
        return items[0] if items else None

    params: dict[str, str] = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "statistics,snippet,brandingSettings",
    }
    if use_handle:
        params["forHandle"] = cache_value
    else:
        params["id"] = channel_id
    try:
        response = httpx.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        store_cached_youtube_api(cache_kind, cache_value, payload)
        items = payload.get("items") or []
        if not items:
            return None
        return items[0]
    except Exception as exc:
        log.debug("_channels_api_fetch failed (handle=%s, id=%s): %s", handle, channel_id, exc)
        return None


def _videos_api_fetch(video_ids: list[str]) -> dict[str, dict]:
    if not settings.YOUTUBE_API_KEY or not video_ids:
        return {}
    cache_kind = "videos"
    cache_value = ",".join(video_ids)

    cached = get_cached_youtube_api(cache_kind, cache_value)
    if cached is not None:
        items = cached.get("items") or []
        return {item["id"]: item for item in items if isinstance(item, dict) and "id" in item}

    try:
        response = httpx.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "key": settings.YOUTUBE_API_KEY,
                "id": cache_value,
                "part": "statistics,snippet",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        store_cached_youtube_api(cache_kind, cache_value, payload)
        items = payload.get("items") or []
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


def _build_profile_from_channel(
    normalized: str,
    handle: str,
    channel_raw: dict,
    posts: list[dict],
    video_stats_map: dict[str, dict],
) -> PlatformProfile:
    stats = (channel_raw.get("statistics") or {}) if isinstance(channel_raw, dict) else {}
    snippet = (channel_raw.get("snippet") or {}) if isinstance(channel_raw, dict) else {}
    title = str(snippet.get("title") or "").replace(" - YouTube", "").strip() or handle
    description = str(snippet.get("description") or "")
    subscribers = _stats_or_none(stats, "subscriberCount")
    lifetime_views = _stats_or_none(stats, "viewCount")
    video_count = _stats_or_none(stats, "videoCount")
    channel_id = str(channel_raw.get("id") or "")
    verified = bool(
        snippet.get("customUrl")
        and (channel_raw.get("status") or {}).get("isLinked")
    )

    for post in posts:
        vid = post.get("id")
        vs = video_stats_map.get(vid, {}) if vid else {}
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


def _fetch_via_api(normalized: str, handle: str) -> PlatformProfile | None:
    """API-only fast path. Returns ``None`` if the handle can't be resolved."""
    if not settings.YOUTUBE_API_KEY or not handle:
        return None
    channel_raw = _channels_api_fetch(handle=handle)
    if channel_raw is None:
        return None
    channel_id = str(channel_raw.get("id") or "")
    if not channel_id:
        return None
    posts = _rss_posts(channel_id)
    video_ids = [p["id"] for p in posts if p.get("id")]
    video_stats_map = _videos_api_fetch(video_ids) if video_ids else {}
    return _build_profile_from_channel(normalized, handle, channel_raw, posts, video_stats_map)


def fetch_youtube_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url)
    handle = handle_from_url(normalized)

    # Fast path: API key + handle present → skip the HTML scrape entirely.
    if settings.YOUTUBE_API_KEY and handle:
        try:
            api_profile = _fetch_via_api(normalized, handle)
            if api_profile is not None:
                return api_profile
        except Exception as exc:
            log.debug("fetch_youtube_profile: API fast path failed for %s: %s", normalized, exc)

    try:
        html = _fetch_html(normalized)
        description = meta_content(html, "description") or meta_content(html, "og:description")
        title = meta_content(html, "og:title") or handle
        channel_id = _channel_id(html)
        for block in json_ld_blocks(html):
            title = title or str(block.get("name") or "")
            description = description or str(block.get("description") or "")

        if settings.YOUTUBE_API_KEY and handle and not channel_id:
            handle_channel = _channels_api_fetch(handle=handle)
            if handle_channel is not None:
                channel_id = str(handle_channel.get("id") or channel_id)

        posts = _rss_posts(channel_id)

        if settings.YOUTUBE_API_KEY and channel_id:
            channel_raw = _channels_api_fetch(channel_id=channel_id)
            if channel_raw is not None:
                video_ids = [p["id"] for p in posts if p.get("id")]
                video_stats_map = _videos_api_fetch(video_ids) if video_ids else {}
                return _build_profile_from_channel(normalized, handle, channel_raw, posts, video_stats_map)

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
