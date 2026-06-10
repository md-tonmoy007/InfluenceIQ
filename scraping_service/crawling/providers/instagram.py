from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from scraping_service.crawling.contracts import normalize_url
from scraping_service.crawling.providers.base import PlatformProfile
from scraping_service.crawling.providers.utils import handle_from_url, meta_content

INSTAGRAM_APP_ID = "936619743392459"


def _actor_path(actor_id: str) -> str:
    return actor_id.replace("/", "~")


def _pick_first_profile(items: Any, username: str) -> dict[str, Any] | None:
    if isinstance(items, dict):
        for key in ("items", "data", "results"):
            if isinstance(items.get(key), list):
                items = items[key]
                break
        else:
            return items
    if not isinstance(items, list):
        return None
    lowered = username.casefold()
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_username = str(item.get("username") or item.get("handle") or "").lstrip("@").casefold()
        if raw_username == lowered:
            return item
    return items[0] if items and isinstance(items[0], dict) else None


def _parse_apify_profile(data: dict[str, Any], url: str, username: str) -> PlatformProfile:
    raw_posts = data.get("latestPosts") or data.get("posts") or data.get("edge_owner_to_timeline_media", [])
    posts: list[dict[str, Any]] = []
    comments: list[str] = []
    engagement_values: list[int] = []
    if isinstance(raw_posts, dict):
        raw_posts = raw_posts.get("edges", [])
    for raw in raw_posts[:12] if isinstance(raw_posts, list) else []:
        post = raw.get("node", raw) if isinstance(raw, dict) else {}
        caption = str(post.get("caption") or post.get("text") or post.get("title") or "")
        likes = post.get("likesCount") or post.get("likeCount") or post.get("likes") or post.get("edge_liked_by", {}).get("count")
        comments_count = post.get("commentsCount") or post.get("commentCount") or post.get("comments") or post.get("edge_media_to_comment", {}).get("count")
        if isinstance(likes, int | float):
            engagement_values.append(int(likes))
        posts.append({
            "id": post.get("id"),
            "shortcode": post.get("shortCode") or post.get("shortcode"),
            "caption": caption,
            "likes": likes,
            "comments_count": comments_count,
            "views": post.get("videoViewCount") or post.get("videoPlayCount") or post.get("views"),
            "taken_at": post.get("timestamp") or post.get("takenAt") or post.get("taken_at_timestamp"),
            "url": post.get("url"),
        })
        if caption:
            comments.append(caption)
    followers = data.get("followersCount") or data.get("followers") or data.get("edge_followed_by", {}).get("count")
    following = data.get("followsCount") or data.get("followingCount") or data.get("following") or data.get("edge_follow", {}).get("count")
    avg_engagement = int(sum(engagement_values) / len(engagement_values)) if engagement_values else None
    external_url = data.get("externalUrl") or data.get("external_url") or data.get("website")
    profile_url = data.get("url") or url
    return PlatformProfile(
        platform="instagram",
        url=url,
        handle=str(data.get("username") or username).lstrip("@"),
        name=str(data.get("fullName") or data.get("full_name") or data.get("name") or username),
        bio=str(data.get("biography") or data.get("bio") or ""),
        followers=int(followers) if isinstance(followers, int | float) else None,
        following=int(following) if isinstance(following, int | float) else None,
        average_engagement=avg_engagement,
        verified=bool(data.get("verified") or data.get("isVerified") or data.get("is_verified")),
        profile_urls=[value for value in [profile_url, external_url] if value],
        posts=posts,
        comments=comments[:50],
        raw={"source": "apify", "id": data.get("id"), "input_url": url},
        provider="apify_instagram",
    )


def _fetch_apify_profile(url: str, username: str) -> PlatformProfile | None:
    if not settings.APIFY_API_TOKEN:
        return None
    actor = _actor_path(settings.APIFY_INSTAGRAM_ACTOR)
    endpoint = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
    payloads = [
        {"usernames": [username], "resultsLimit": 1},
        {"directUrls": [url], "resultsLimit": 1},
        {"startUrls": [{"url": url}], "resultsLimit": 1},
    ]
    last_error: Exception | None = None
    for payload in payloads:
        try:
            response = httpx.post(
                endpoint,
                params={"token": settings.APIFY_API_TOKEN, "clean": "true"},
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            item = _pick_first_profile(response.json(), username)
            if item:
                return _parse_apify_profile(item, url, username)
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return None


def _parse_user(data: dict[str, Any]) -> PlatformProfile:
    username = str(data.get("username") or "")
    videos = data.get("edge_felix_video_timeline", {}).get("edges", []) or []
    images = data.get("edge_owner_to_timeline_media", {}).get("edges", []) or []
    posts: list[dict[str, Any]] = []
    comments: list[str] = []
    engagement_values: list[int] = []
    for edge in [*videos, *images][:12]:
        node = edge.get("node", {}) if isinstance(edge, dict) else {}
        captions = [
            caption.get("node", {}).get("text", "")
            for caption in node.get("edge_media_to_caption", {}).get("edges", []) or []
            if isinstance(caption, dict)
        ]
        likes = node.get("edge_liked_by", {}).get("count") or 0
        comment_count = node.get("edge_media_to_comment", {}).get("count") or 0
        if likes:
            engagement_values.append(int(likes))
        posts.append({
            "id": node.get("id"),
            "shortcode": node.get("shortcode"),
            "caption": " ".join(captions),
            "likes": likes,
            "comments_count": comment_count,
            "views": node.get("video_view_count"),
            "taken_at": node.get("taken_at_timestamp"),
        })
        comments.extend(captions)
    avg_engagement = int(sum(engagement_values) / len(engagement_values)) if engagement_values else None
    profile_url = f"https://instagram.com/{username}" if username else ""
    bio_links = [
        str(link.get("url", ""))
        for link in data.get("bio_links", []) or []
        if isinstance(link, dict) and link.get("url")
    ]
    return PlatformProfile(
        platform="instagram",
        url=profile_url,
        handle=username,
        name=str(data.get("full_name") or username),
        bio=str(data.get("biography") or ""),
        followers=data.get("edge_followed_by", {}).get("count"),
        following=data.get("edge_follow", {}).get("count"),
        average_engagement=avg_engagement,
        verified=bool(data.get("is_verified")),
        profile_urls=[url for url in [profile_url, *bio_links] if url],
        posts=posts,
        comments=[comment for comment in comments if comment][:50],
        raw={"id": data.get("id"), "category": data.get("category_name")},
        provider="instagram_web_profile",
    )


def fetch_instagram_profile(url: str) -> PlatformProfile | None:
    normalized = normalize_url(url)
    username = handle_from_url(normalized)
    try:
        apify_profile = _fetch_apify_profile(normalized, username)
        if apify_profile is not None:
            return apify_profile
    except Exception:
        pass
    try:
        response = httpx.get(
            "https://i.instagram.com/api/v1/users/web_profile_info/",
            params={"username": username},
            headers={
                "User-Agent": "Mozilla/5.0",
                "x-ig-app-id": INSTAGRAM_APP_ID,
                "Accept": "application/json",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        user = payload.get("data", {}).get("user")
        if isinstance(user, dict):
            profile = _parse_user(user)
            profile.url = normalized
            return profile
        raise ValueError("Instagram response did not include data.user")
    except Exception as api_exc:
        try:
            html = httpx.get(normalized, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).text
            description = meta_content(html, "og:description") or meta_content(html, "description")
            return PlatformProfile(
                platform="instagram",
                url=normalized,
                handle=username,
                name=username,
                bio=description or "Instagram profile metadata only.",
                profile_urls=[normalized],
                provider="instagram_meta",
                error=None if description else str(api_exc),
            )
        except Exception as html_exc:
            return PlatformProfile(
                platform="instagram",
                url=normalized,
                handle=username,
                name=username,
                bio="Instagram profile fetch failed; using URL-derived profile identity.",
                profile_urls=[normalized],
                provider="instagram_fallback",
                error=f"{api_exc}; {html_exc}",
            )
