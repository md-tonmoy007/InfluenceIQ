from __future__ import annotations

import redis

from app.config import settings

# Shared Redis client with response decoding enabled
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
