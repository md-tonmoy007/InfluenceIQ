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
    author = data.get("author") or data.get("user") or {}
    if not isinstance(author, dict):
        author = {}
    username = str(
        data.get("userName")
        or data.get("username")
        or author.get("userName")
        or author.get("username")
        or handle
    ).lstrip("@")
    name = str(data.get("name") or author.get("name") or author.get("displayName") or username)
    bio = str(data.get("description") or data.get("bio") or author.get("description") or author.get("bio") or "")
    followers = (
        data.get("followers")
        or data.get("followersCount")
        or author.get("followers")
        or author.get("followersCount")
    )
    following = data.get("following") or data.get("followingCount") or author.get("following") or author.get("followingCount")
    verified = bool(
        data.get("isVerified")
        or data.get("verified")
        or author.get("isVerified")
        or author.get("verified")
    )

    raw_posts = data.get("tweets") or data.get("latestTweets") or data.get("posts") or []
    if data.get("text") and not raw_posts:
        raw_posts = [data]
    posts: list[dict[str, Any]] = []
    comments: list[str] = []
    engagement_values: list[int] = []
    for raw in raw_posts[:12] if isinstance(raw_posts, list) else []:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or raw.get("fullText") or raw.get("description") or "")
        likes = raw.get("likeCount") or raw.get("likes") or raw.get("favoriteCount")
        reply_count = raw.get("replyCount") or raw.get("commentsCount")
        if isinstance(likes, int | float):
            engagement_values.append(int(likes))
        posts.append({
            "id": raw.get("id") or raw.get("tweetId"),
            "caption": text,
            "likes": likes,
            "comments_count": reply_count,
            "url": raw.get("url") or raw.get("twitterUrl"),
            "taken_at": raw.get("createdAt") or raw.get("timestamp"),
        })
        if text:
            comments.append(text)

    avg_engagement = int(sum(engagement_values) / len(engagement_values)) if engagement_values else None
    profile_url = data.get("url") or author.get("url") or url
    return PlatformProfile(
        platform="x",
        url=url,
        handle=username,
        name=name.replace(" / X", "").replace(" on X", "").strip(),
        bio=bio,
        followers=int(followers) if isinstance(followers, int | float) else compact_number(str(followers)),
        following=int(following) if isinstance(following, int | float) else compact_number(str(following)),
        average_engagement=avg_engagement,
        verified=verified,
        profile_urls=[profile_url],
        posts=posts,
        comments=comments[:50],
        raw={"source": "apify", "input_url": url},
        provider="apify_x",
    )


def _fetch_apify_profile(url: str, handle: str) -> PlatformProfile | None:
    limit = min(settings.PLATFORM_POST_LIMIT, 12)
    payloads = profile_payloads(url, handle, limit=limit)
    payloads.extend([
        {"startUrls": [{"url": url}], "maxItems": limit},
        {"searchTerms": [f"from:{handle.lstrip('@')}"], "maxItems": limit},
    ])
    item = run_actor_sync(settings.APIFY_X_ACTOR, payloads, username=handle)
    if item:
        return _parse_apify_profile(item, url, handle)
    return None


def fetch_x_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url).replace("https://twitter.com/", "https://x.com/")
    handle = handle_from_url(normalized)
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
