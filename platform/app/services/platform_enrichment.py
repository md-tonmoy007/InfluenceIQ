from __future__ import annotations

import json
import re
from statistics import mean
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.config import settings
from scoring_service.extraction.handles import normalize_profile_url

_JSON_SCRIPT_RE = re.compile(
    r"<script[^>]+(?:id|data-hydration-id)=[\"'](?P<id>[^\"']+)[\"'][^>]*>(?P<body>.*?)</script>",
    flags=re.IGNORECASE | re.DOTALL,
)


def normalize_platform_identity(url: str) -> dict[str, Any] | None:
    canonical = normalize_profile_url(url)
    if not canonical:
        return None
    parsed = urlsplit(canonical)
    host = (parsed.hostname or "").casefold().removeprefix("www.").removeprefix("m.")
    segments = [segment for segment in parsed.path.split("/") if segment]

    if host == "youtube.com" and segments:
        head = segments[0]
        if head.startswith("@"):
            handle = head.removeprefix("@")
            return {
                "platform": "youtube",
                "canonical_profile_url": f"https://youtube.com/@{handle}",
                "handle_or_username": handle.casefold(),
                "channel_id": None,
                "identity_type": "handle",
            }
        if head == "channel" and len(segments) >= 2:
            channel_id = segments[1]
            return {
                "platform": "youtube",
                "canonical_profile_url": f"https://youtube.com/channel/{channel_id}",
                "handle_or_username": "",
                "channel_id": channel_id,
                "identity_type": "channel",
            }
        if head in {"c", "user"} and len(segments) >= 2:
            username = segments[1]
            return {
                "platform": "youtube",
                "canonical_profile_url": f"https://youtube.com/{head}/{username}",
                "handle_or_username": username.casefold(),
                "channel_id": None,
                "identity_type": head,
            }

    if host == "tiktok.com" and segments and segments[0].startswith("@"):
        username = segments[0].removeprefix("@")
        return {
            "platform": "tiktok",
            "canonical_profile_url": f"https://tiktok.com/@{username}",
            "handle_or_username": username.casefold(),
            "channel_id": None,
            "identity_type": "username",
        }
    return None


def choose_preferred_identity(urls: list[str]) -> dict[str, Any] | None:
    identities = [identity for url in urls if (identity := normalize_platform_identity(url))]
    if not identities:
        return None
    identities.sort(key=lambda item: (0 if item["platform"] == "youtube" else 1, item["canonical_profile_url"]))
    return identities[0]


def _to_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = re.sub(r"[^\d]", "", str(value))
    return int(text or "0")


def _safe_mean(values: list[float]) -> float:
    return float(mean(values)) if values else 0.0


def _youtube_api_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    merged = {**params, "key": settings.YOUTUBE_API_KEY}
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(f"https://www.googleapis.com/youtube/v3/{endpoint}", params=merged)
        response.raise_for_status()
        return response.json()


def _youtube_video_metrics(videos: list[dict[str, Any]]) -> dict[str, Any]:
    rates: list[float] = []
    view_counts: list[int] = []
    like_counts: list[int] = []
    comment_counts: list[int] = []
    sample: list[dict[str, Any]] = []
    for video in videos[:10]:
        stats = video.get("statistics") or {}
        video_id = str(video.get("id") or "")
        views = _to_int(stats.get("viewCount"))
        likes = _to_int(stats.get("likeCount"))
        comments = _to_int(stats.get("commentCount"))
        rate = (likes + comments) / max(views, 1)
        rates.append(rate)
        view_counts.append(views)
        like_counts.append(likes)
        comment_counts.append(comments)
        sample.append(
            {
                "video_id": video_id,
                "views": views,
                "likes": likes,
                "comments": comments,
            }
        )
    return {
        "engagement_rate": _safe_mean(rates),
        "average_views": round(_safe_mean([float(value) for value in view_counts]), 2),
        "average_likes": round(_safe_mean([float(value) for value in like_counts]), 2),
        "average_comments": round(_safe_mean([float(value) for value in comment_counts]), 2),
        "sample_size": len(sample),
        "recent_videos": sample,
        "formula": "(likes+comments)/views",
    }


def enrich_youtube_profile(identity: dict[str, Any]) -> dict[str, Any]:
    base = {
        "platform": "youtube",
        "identity": identity,
        "status": "discovered_only",
        "name": "",
        "handle": identity.get("handle_or_username") or "",
        "followers": 0,
        "engagement_rate": 0.0,
        "source_payload": {"identity": identity, "status": "discovered_only"},
    }
    if not settings.YOUTUBE_API_KEY:
        base["status"] = "missing_api_key"
        base["source_payload"]["status"] = "missing_api_key"
        return base

    channel_lookup = {"part": "snippet,statistics"}
    if identity.get("channel_id"):
        channel_lookup["id"] = identity["channel_id"]
    elif identity.get("identity_type") == "handle":
        channel_lookup["forHandle"] = identity["handle_or_username"]
    elif identity.get("identity_type") == "user":
        channel_lookup["forUsername"] = identity["handle_or_username"]
    else:
        base["status"] = "unsupported_lookup"
        base["source_payload"]["status"] = "unsupported_lookup"
        return base

    payload = _youtube_api_get("channels", channel_lookup)
    items = payload.get("items") or []
    if not items:
        base["status"] = "lookup_failed"
        base["source_payload"]["status"] = "lookup_failed"
        return base

    channel = items[0]
    snippet = channel.get("snippet") or {}
    statistics = channel.get("statistics") or {}
    channel_id = str(channel.get("id") or identity.get("channel_id") or "")
    video_search = _youtube_api_get(
        "search",
        {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "order": "date",
            "maxResults": 10,
        },
    )
    video_ids = [
        str((item.get("id") or {}).get("videoId") or "")
        for item in (video_search.get("items") or [])
        if (item.get("id") or {}).get("videoId")
    ]
    video_stats: list[dict[str, Any]] = []
    if video_ids:
        video_payload = _youtube_api_get(
            "videos",
            {"part": "statistics", "id": ",".join(video_ids[:10])},
        )
        video_stats = list(video_payload.get("items") or [])
    metrics = _youtube_video_metrics(video_stats)
    handle = str(
        (snippet.get("customUrl") or "").removeprefix("@")
        or identity.get("handle_or_username")
        or ""
    ).casefold()
    canonical_url = f"https://youtube.com/@{handle}" if handle else identity["canonical_profile_url"]
    source_payload = {
        "identity": {**identity, "channel_id": channel_id, "canonical_profile_url": canonical_url},
        "status": "enriched",
        "description": str(snippet.get("description") or ""),
        "channel_title": str(snippet.get("title") or ""),
        "thumbnails": snippet.get("thumbnails") or {},
        "subscriber_count": _to_int(statistics.get("subscriberCount")),
        "video_count": _to_int(statistics.get("videoCount")),
        "view_count": _to_int(statistics.get("viewCount")),
        "engagement": metrics,
    }
    return {
        "platform": "youtube",
        "identity": source_payload["identity"],
        "status": "enriched",
        "name": source_payload["channel_title"],
        "handle": handle,
        "followers": source_payload["subscriber_count"],
        "engagement_rate": metrics["engagement_rate"],
        "source_payload": source_payload,
    }


def _extract_embedded_json(html: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for match in _JSON_SCRIPT_RE.finditer(html or ""):
        script_id = str(match.group("id") or "")
        if script_id not in {"SIGI_STATE", "__UNIVERSAL_DATA_FOR_REHYDRATION__"}:
            continue
        body = str(match.group("body") or "").strip()
        if not body:
            continue
        try:
            payloads.append(json.loads(body))
        except json.JSONDecodeError:
            continue
    return payloads


def _walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _find_first_user(payloads: list[dict[str, Any]], username: str) -> dict[str, Any]:
    for payload in payloads:
        for node in _walk(payload):
            unique_id = str(node.get("uniqueId") or node.get("unique_id") or "").casefold()
            if unique_id == username.casefold():
                return node
    return {}


def _find_recent_posts(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for payload in payloads:
        for node in _walk(payload):
            if "stats" not in node:
                continue
            stats = node.get("stats") or {}
            post = node.get("video") or node.get("item") or {}
            if not any(key in stats for key in ("playCount", "diggCount", "commentCount", "shareCount")):
                continue
            posts.append(
                {
                    "id": str(node.get("id") or post.get("id") or ""),
                    "views": _to_int(stats.get("playCount")),
                    "likes": _to_int(stats.get("diggCount")),
                    "comments": _to_int(stats.get("commentCount")),
                    "shares": _to_int(stats.get("shareCount")),
                }
            )
    unique: dict[str, dict[str, Any]] = {}
    for post in posts:
        if post["id"]:
            unique[post["id"]] = post
    return list(unique.values())[:10]


def _tiktok_post_metrics(posts: list[dict[str, Any]], follower_count: int) -> dict[str, Any]:
    rates: list[float] = []
    formula = "(likes+comments+shares)/views"
    for post in posts:
        numerator = post["likes"] + post["comments"] + post["shares"]
        views = post["views"]
        if views > 0:
            rates.append(numerator / max(views, 1))
        else:
            formula = "(likes+comments+shares)/followers"
            rates.append(numerator / max(follower_count, 1))
    return {
        "engagement_rate": _safe_mean(rates),
        "sample_size": len(posts),
        "recent_posts": posts,
        "formula": formula,
    }


def enrich_tiktok_profile(identity: dict[str, Any], html: str) -> dict[str, Any]:
    username = str(identity.get("handle_or_username") or "")
    payloads = _extract_embedded_json(html)
    user = _find_first_user(payloads, username) if username else {}
    stats = user.get("stats") or {}
    followers = _to_int(stats.get("followerCount") or stats.get("followers"))
    posts = _find_recent_posts(payloads)
    engagement = _tiktok_post_metrics(posts, followers)
    source_payload = {
        "identity": identity,
        "status": "enriched" if user or posts else "parse_partial",
        "display_name": str(user.get("nickname") or user.get("displayName") or ""),
        "bio": str(user.get("signature") or user.get("bio") or ""),
        "follower_count": followers,
        "following_count": _to_int(stats.get("followingCount") or stats.get("following")),
        "total_likes": _to_int(stats.get("heartCount") or stats.get("likes")),
        "verified": bool(user.get("verified")),
        "engagement": engagement,
    }
    return {
        "platform": "tiktok",
        "identity": identity,
        "status": source_payload["status"],
        "name": source_payload["display_name"],
        "handle": username,
        "followers": followers,
        "engagement_rate": engagement["engagement_rate"],
        "source_payload": source_payload,
    }


def enrich_platform_profile(identity: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    if identity["platform"] == "youtube":
        return enrich_youtube_profile(identity)
    if identity["platform"] == "tiktok":
        return enrich_tiktok_profile(identity, str(page.get("html") or ""))
    return {
        "platform": identity["platform"],
        "identity": identity,
        "status": "unsupported_platform",
        "name": "",
        "handle": identity.get("handle_or_username") or "",
        "followers": 0,
        "engagement_rate": 0.0,
        "source_payload": {"identity": identity, "status": "unsupported_platform"},
    }
