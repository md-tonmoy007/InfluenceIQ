"""Redis-backed URL cache and provider circuit breaker."""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any

import redis

from backend.core.config import settings
from backend.pipeline.content.contracts import url_cache_key

URL_CACHE_TTL_SECONDS = 48 * 60 * 60
PROVIDER_FAIL_PREFIX = "role4:provider_fail:"
PROVIDER_FAIL_THRESHOLD = 5
PROVIDER_FAIL_WINDOW = 60  # seconds
PROVIDER_COOLDOWN = 300    # 5 minutes

# YouTube Data API v3 response cache — dedupes calls within and across
# campaigns when multiple influencers share a channel or re-fetch the
# same handle.
YOUTUBE_API_CACHE_PREFIX = "role4:youtube_api:"
YOUTUBE_API_CACHE_TTL = 6 * 60 * 60  # 6 hours
YOUTUBE_RSS_CACHE_TTL = 60 * 60      # 1 hour (RSS updates when creators post)


@lru_cache(maxsize=1)
def _redis_connection() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


def redis_client() -> redis.Redis:
    """Return the shared Redis client."""
    return _redis_connection()


def get_cached_page(url: str) -> dict[str, Any] | None:
    try:
        raw = redis_client().get(url_cache_key(url))
    except redis.RedisError:
        return None
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        payload = json.loads(str(raw))
    except json.JSONDecodeError:
        return None
    payload["cached"] = True
    return payload


def store_cached_page(url: str, payload: dict[str, Any]) -> None:
    try:
        redis_client().setex(url_cache_key(url), URL_CACHE_TTL_SECONDS, json.dumps(payload, sort_keys=True))
    except redis.RedisError:
        return


# ---------------------------------------------------------------------------
# Provider circuit breaker
# ---------------------------------------------------------------------------


def _provider_fail_key(provider: str) -> str:
    return f"{PROVIDER_FAIL_PREFIX}{provider}"


def record_provider_failure(provider: str) -> bool:
    """Record a failure for *provider* and return ``True`` if the breaker
    should open (threshold exceeded).
    """
    key = _provider_fail_key(provider)
    now = time.time()
    try:
        client = redis_client()
        pipeline = client.pipeline()
        pipeline.zadd(key, {str(now): now})
        pipeline.zremrangebyscore(key, 0, now - PROVIDER_FAIL_WINDOW)
        pipeline.expire(key, PROVIDER_COOLDOWN)
        pipeline.zcard(key)
        _, _, _, count = pipeline.execute()
        return int(count) >= PROVIDER_FAIL_THRESHOLD
    except redis.RedisError:
        return False


def provider_is_available(provider: str) -> bool:
    """Check whether *provider* is currently allowed to serve requests."""
    if provider in ("web", "fallback", "httpx"):
        return True  # generic fetchers are never circuit-broken
    key = _provider_fail_key(provider)
    try:
        client = redis_client()
        cooldown_ttl = client.ttl(key)
        return cooldown_ttl <= 0  # -1 = no key, -2 = expired
    except redis.RedisError:
        return True


def reset_provider_breaker(provider: str) -> None:
    """Manually reset the breaker for *provider*."""
    try:
        redis_client().delete(_provider_fail_key(provider))
    except redis.RedisError:
        return


# ---------------------------------------------------------------------------
# YouTube Data API v3 response cache
# ---------------------------------------------------------------------------


def _youtube_api_cache_key(kind: str, value: str) -> str:
    return f"{YOUTUBE_API_CACHE_PREFIX}{kind}:{value}"


def get_cached_youtube_api(kind: str, value: str) -> Any | None:
    """Return a cached ``channels.list`` / ``videos.list`` / RSS response.

    ``kind`` is one of ``"handle"``, ``"id"``, ``"videos"``, ``"rss"``.
    ``value`` is the ``forHandle``/``id``/comma-joined video ids/``channel_id``
    string passed to the API. Returns ``None`` on miss or any Redis error.
    """
    try:
        raw = redis_client().get(_youtube_api_cache_key(kind, value))
    except redis.RedisError:
        return None
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return None


def store_cached_youtube_api(kind: str, value: str, payload: Any, ttl: int | None = None) -> None:
    """Persist a successful API response for the configured TTL."""
    try:
        redis_client().setex(
            _youtube_api_cache_key(kind, value),
            ttl if ttl is not None else YOUTUBE_API_CACHE_TTL,
            json.dumps(payload, sort_keys=True, default=str),
        )
    except redis.RedisError:
        return


def clear_youtube_api_cache() -> int:
    """Delete all cached YouTube API responses. Returns the count deleted."""
    try:
        client = redis_client()
        deleted = 0
        for key in client.scan_iter(match=f"{YOUTUBE_API_CACHE_PREFIX}*"):
            client.delete(key)
            deleted += 1
        return deleted
    except redis.RedisError:
        return 0
