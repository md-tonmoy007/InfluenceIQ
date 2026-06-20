from __future__ import annotations

import time

import redis

from backend.pipeline.content.cache import redis_client
from backend.pipeline.content.contracts import domain_for_url, platform_for_url

SOCIAL_MIN_INTERVAL_SECONDS = 2.0
WEB_MIN_INTERVAL_SECONDS = 0.35


def throttle_delay_seconds(url: str) -> float:
    platform = platform_for_url(url)
    min_interval = SOCIAL_MIN_INTERVAL_SECONDS if platform != "web" else WEB_MIN_INTERVAL_SECONDS
    domain = domain_for_url(url)
    key = f"rate_limit:{domain}"
    now = time.time()
    try:
        raw = redis_client().get(key)
        last_seen = float(raw.decode("utf-8") if isinstance(raw, bytes) else raw) if raw else 0.0
        wait_for = max(0.0, min_interval - (now - last_seen))
        if wait_for <= 0:
            redis_client().setex(key, 10, str(now))
        return round(wait_for, 3)
    except (redis.RedisError, TypeError, ValueError):
        return 0.0
