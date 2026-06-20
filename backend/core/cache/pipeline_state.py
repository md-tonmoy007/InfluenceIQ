from __future__ import annotations

import redis.asyncio as aioredis

from backend.core.cache.redis_client import redis_client

# Redis hash key pattern for pipeline state
STATE_KEY_PREFIX = "pipeline_state:"
STATE_TTL = 7200  # 2 hours


def initialize_pipeline_state(campaign_id: str, total_urls: int = 0) -> None:
    """Initializes the campaign execution state hash in Redis with default values."""
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    initial_state = {
        "campaign_id": campaign_id,
        "phase": "initializing",
        "urls_discovered": str(total_urls),
        "urls_scraped": "0",
        "urls_failed": "0",
        "influencers_found": "0",
        "scores_computed": "0",
    }
    redis_client.hset(key, mapping=initial_state)
    redis_client.expire(key, STATE_TTL)


def update_pipeline_state(campaign_id: str, **fields) -> None:
    """Updates fields in the pipeline state hash and extends/renews its TTL."""
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    mapping = {k: str(v) for k, v in fields.items()}
    if mapping:
        redis_client.hset(key, mapping=mapping)
    redis_client.expire(key, STATE_TTL)


def get_pipeline_state(campaign_id: str) -> dict | None:
    """Retrieves and normalizes the pipeline state from Redis (sync)."""
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    state = redis_client.hgetall(key)
    if not state:
        return None
    return _coerce_int_columns(state)


async def aget_pipeline_state(
    async_redis: aioredis.Redis, campaign_id: str
) -> dict | None:
    """Async variant of :func:`get_pipeline_state`."""
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    state = await async_redis.hgetall(key)
    if not state:
        return None
    return _coerce_int_columns(state)


async def aupdate_pipeline_state(
    async_redis: aioredis.Redis, campaign_id: str, **fields
) -> None:
    """Async variant of :func:`update_pipeline_state`."""
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    mapping = {k: str(v) for k, v in fields.items()}
    if mapping:
        await async_redis.hset(key, mapping=mapping)
    await async_redis.expire(key, STATE_TTL)


def _coerce_int_columns(state: dict) -> dict:
    """Cast the documented integer columns back to ``int`` after the Redis round-trip."""
    int_cols = (
        "urls_discovered",
        "urls_scraped",
        "urls_failed",
        "influencers_found",
        "scores_computed",
    )
    for col in int_cols:
        if col in state:
            try:
                state[col] = int(state[col])
            except ValueError:
                state[col] = 0
    return state


__all__ = [
    "STATE_KEY_PREFIX",
    "STATE_TTL",
    "aget_pipeline_state",
    "aupdate_pipeline_state",
    "get_pipeline_state",
    "initialize_pipeline_state",
    "update_pipeline_state",
]
