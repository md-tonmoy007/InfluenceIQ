"""Instagram comment scraper via Apify."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.core.config import settings
from backend.pipeline.content.cache import (
    provider_is_available,
    record_provider_failure,
)
from backend.pipeline.content.providers.apify_client import run_actor_sync_all
from backend.pipeline.content.providers.comments.base import RawComment

log = logging.getLogger(__name__)


def _parse_timestamp(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.fromtimestamp(int(value), tz=UTC).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None


def fetch_instagram_post_comments(post_url: str, limit: int) -> list[RawComment]:
    """Fetch comments for a single Instagram post via Apify."""
    if not settings.APIFY_API_TOKEN or not post_url:
        return []

    provider = "apify_instagram_comments"
    if not provider_is_available(provider):
        return []

    payloads = [
        {"directUrls": [post_url], "resultsLimit": limit},
        {"startUrls": [{"url": post_url}], "resultsLimit": limit},
    ]

    try:
        items = run_actor_sync_all(
            settings.APIFY_INSTAGRAM_COMMENTS_ACTOR,
            payloads,
            timeout=180,
        )
    except Exception as exc:
        log.warning("fetch_instagram_post_comments failed url=%s: %s", post_url, exc)
        record_provider_failure(provider)
        return []

    comments: list[RawComment] = []
    for item in items[:limit]:
        comment = _parse_item(item)
        if comment:
            comments.append(comment)
    return comments


def _parse_item(item: dict) -> RawComment | None:
    if not isinstance(item, dict):
        return None
    text = str(item.get("text") or item.get("caption") or "").strip()
    if not text:
        return None
    owner = item.get("owner") or {}
    author_key = str(
        item.get("ownerUsername")
        or item.get("username")
        or (owner.get("username") if isinstance(owner, dict) else None)
        or ""
    )
    return RawComment(
        external_id=str(item.get("id") or ""),
        text=text,
        author_key=author_key,
        like_count=_int_or_none(item.get("likesCount")),
        published_at=_parse_timestamp(item.get("timestamp")),
        reply_count=None,
    )


def _int_or_none(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
