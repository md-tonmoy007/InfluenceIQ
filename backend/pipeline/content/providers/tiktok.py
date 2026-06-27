from __future__ import annotations

import re
from typing import Any

import httpx

from backend.core.config import settings
from backend.pipeline.content.contracts import compact_number, normalize_url
from backend.pipeline.content.providers.apify_client import profile_payloads, run_actor_sync
from backend.pipeline.content.providers.base import PlatformProfile
from backend.pipeline.content.providers.utils import handle_from_url, meta_content


def _parse_apify_profile(data: dict[str, Any], url: str, handle: str) -> PlatformProfile:
    author = data.get("authorMeta") or data.get("author") or {}
    if not isinstance(author, dict):
        author = {}
    username = str(
        data.get("uniqueId")
        or author.get("uniqueId")
        or author.get("name")
        or data.get("username")
        or handle
    ).lstrip("@")
    name = str(
        author.get("nickName")
        or author.get("name")
        or data.get("nickname")
        or data.get("title")
        or username
    )
    bio = str(author.get("signature") or data.get("signature") or data.get("bio") or data.get("description") or "")
    followers = (
        author.get("fans")
        or author.get("followerCount")
        or data.get("followers")
        or data.get("followerCount")
    )
    likes = author.get("heart") or author.get("diggCount") or data.get("likes") or data.get("heartCount")
    verified = bool(
        author.get("verified")
        or data.get("verified")
        or data.get("isVerified")
    )

    raw_posts = data.get("videos") or data.get("latestPosts") or data.get("posts") or []
    if isinstance(data.get("video"), dict):
        extra = raw_posts if isinstance(raw_posts, list) else []
        raw_posts = [data["video"], *extra]
    posts: list[dict[str, Any]] = []
    comments: list[str] = []
    engagement_values: list[int] = []
    for raw in raw_posts[:12] if isinstance(raw_posts, list) else []:
        if not isinstance(raw, dict):
            continue
        caption = str(raw.get("text") or raw.get("desc") or raw.get("description") or raw.get("title") or "")
        play_count = raw.get("playCount") or raw.get("views") or raw.get("diggCount")
        comment_count = raw.get("commentCount") or raw.get("commentsCount")
        if isinstance(play_count, int | float):
            engagement_values.append(int(play_count))
        posts.append({
            "id": raw.get("id") or raw.get("videoId"),
            "caption": caption,
            "views": play_count,
            "comments_count": comment_count,
            "url": raw.get("webVideoUrl") or raw.get("url"),
            "taken_at": raw.get("createTime") or raw.get("timestamp"),
        })
        if caption:
            comments.append(caption)

    avg_engagement = int(sum(engagement_values) / len(engagement_values)) if engagement_values else None
    if avg_engagement is None and isinstance(likes, int | float):
        avg_engagement = int(likes)

    profile_url = data.get("url") or url
    return PlatformProfile(
        platform="tiktok",
        url=url,
        handle=username,
        name=name.replace("| TikTok", "").strip(),
        bio=bio,
        followers=int(followers) if isinstance(followers, int | float) else compact_number(str(followers)),
        average_engagement=avg_engagement,
        verified=verified,
        profile_urls=[profile_url],
        posts=posts,
        comments=comments[:50],
        raw={"source": "apify", "input_url": url},
        provider="apify_tiktok",
    )


def _fetch_apify_profile(url: str, handle: str) -> PlatformProfile | None:
    limit = min(settings.PLATFORM_POST_LIMIT, 12)
    payloads = profile_payloads(url, handle, limit=limit)
    payloads.extend([
        {"profiles": [handle.lstrip("@")], "resultsPerPage": limit},
        {"startUrls": [url], "profileScrapeSections": ["videos"], "maxResults": limit},
    ])
    item = run_actor_sync(settings.APIFY_TIKTOK_ACTOR, payloads, username=handle)
    if item:
        return _parse_apify_profile(item, url, handle)
    return None


def fetch_tiktok_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url)
    handle = handle_from_url(normalized)
    if not handle and "/@" in normalized:
        handle = normalized.split("/@", 1)[1].split("/", 1)[0]
    handle = handle.lstrip("@")
    try:
        apify_profile = _fetch_apify_profile(normalized, handle)
        if apify_profile is not None:
            return apify_profile
    except Exception:
        pass
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
