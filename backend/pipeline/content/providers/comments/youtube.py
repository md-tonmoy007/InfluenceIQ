"""YouTube commentThreads API provider."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from backend.core.config import settings
from backend.pipeline.content.cache import (
    get_cached_youtube_api,
    provider_is_available,
    record_provider_failure,
    store_cached_youtube_api,
)
from backend.pipeline.content.providers.comments.base import RawComment

log = logging.getLogger(__name__)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _serialize(raw: RawComment) -> dict:
    return {
        "external_id": raw.external_id,
        "text": raw.text,
        "author_key": raw.author_key,
        "like_count": raw.like_count,
        "published_at": raw.published_at.isoformat() if raw.published_at else None,
        "reply_count": raw.reply_count,
    }


def _deserialize(data: dict) -> RawComment:
    published_at = data.get("published_at")
    return RawComment(
        external_id=str(data.get("external_id", "")),
        text=str(data.get("text", "")),
        author_key=str(data.get("author_key", "")),
        like_count=_int_or_none(data.get("like_count")),
        published_at=_parse_iso(published_at) if published_at else None,
        reply_count=_int_or_none(data.get("reply_count")),
    )


def fetch_youtube_post_comments(video_id: str, limit: int) -> list[RawComment]:
    """Fetch top-level comments via the official commentThreads API.

    Uses ``order=time`` and paginates via ``nextPageToken`` until ``limit``
    comments are collected. Each page costs 1 quota unit. Cached responses
    are reused across tasks/influencers sharing the same video id.
    """
    if not settings.YOUTUBE_API_KEY or not video_id:
        return []

    provider = "youtube_comments"
    if not provider_is_available(provider):
        return []

    cache_key = f"{video_id}:{limit}"
    cached = get_cached_youtube_api("comments", cache_key)
    if cached is not None:
        return [_deserialize(item) for item in cached if isinstance(item, dict)]

    comments: list[RawComment] = []
    page_token: str | None = None
    page_size = min(100, max(1, limit))

    try:
        while len(comments) < limit:
            params: dict[str, str | int] = {
                "key": settings.YOUTUBE_API_KEY,
                "part": "snippet",
                "videoId": video_id,
                "order": "time",
                "maxResults": page_size,
            }
            if page_token:
                params["pageToken"] = page_token

            response = httpx.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params=params,
                timeout=15,
            )

            if response.status_code == 403:
                payload = response.json() if response.text else {}
                errors = payload.get("error", {}).get("errors", [])
                reason = errors[0].get("reason", "") if errors else ""
                if reason == "commentsDisabled":
                    log.debug("comments disabled for video=%s", video_id)
                    return []

            response.raise_for_status()
            payload = response.json()

            for item in payload.get("items", []) or []:
                comment = _parse_comment_thread_item(item)
                if comment:
                    comments.append(comment)
                if len(comments) >= limit:
                    break

            page_token = payload.get("nextPageToken")
            if not page_token:
                break
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            log.debug("commentThreads 404 for video=%s", video_id)
            return []
        log.warning("fetch_youtube_post_comments failed video=%s: %s", video_id, exc)
        record_provider_failure(provider)
        return []
    except Exception as exc:
        log.warning("fetch_youtube_post_comments failed video=%s: %s", video_id, exc)
        record_provider_failure(provider)
        return []

    store_cached_youtube_api(
        "comments",
        cache_key,
        [_serialize(raw) for raw in comments],
        ttl=settings.COMMENT_CACHE_TTL_SECONDS,
    )
    return comments


def _parse_comment_thread_item(item: dict) -> RawComment | None:
    if not isinstance(item, dict):
        return None
    snippet = item.get("snippet", {})
    top = snippet.get("topLevelComment", {}).get("snippet", {})
    text = str(top.get("textOriginal") or top.get("textDisplay") or "").strip()
    if not text:
        return None
    return RawComment(
        external_id=str(item.get("id", "")),
        text=text,
        author_key=str(top.get("authorChannelId", {}).get("value") or top.get("authorDisplayName") or ""),
        like_count=_int_or_none(top.get("likeCount")),
        published_at=_parse_iso(top.get("publishedAt")),
        reply_count=_int_or_none(snippet.get("totalReplyCount")),
    )


def _int_or_none(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
