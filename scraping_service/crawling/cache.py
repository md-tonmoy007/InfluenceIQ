from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import redis

from app.config import settings
from scraping_service.crawling.contracts import url_cache_key

URL_CACHE_TTL_SECONDS = 48 * 60 * 60


@lru_cache(maxsize=1)
def redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


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
