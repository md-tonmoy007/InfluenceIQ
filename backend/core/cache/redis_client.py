from __future__ import annotations

import redis

from backend.core.config import settings

# Shared Redis client with response decoding enabled
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
