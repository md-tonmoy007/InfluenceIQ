from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis

from app.services.redis_client import redis_client

EVENT_LIST_PREFIX = "pipeline_events:"
EVENT_COUNTER_PREFIX = "event_id_counter:"
PUB_SUB_PREFIX = "campaign:"
EVENT_TTL = 3600  # 1 hour


def _utcnow_iso() -> str:
    """Timezone-aware UTC ``isoformat()`` ending in ``Z``."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def emit_event(campaign_id: str, event_type: str, payload: dict) -> dict:
    """Publishes a structured workflow event to Redis pub/sub and appends it to the replay log.

    Sync API; intended for Celery task bodies. The WebSocket handler uses
    :func:`aemit_event` to avoid blocking the event loop.
    """
    counter_key = f"{EVENT_COUNTER_PREFIX}{campaign_id}"
    event_id = redis_client.incr(counter_key)
    redis_client.expire(counter_key, EVENT_TTL)

    event = {
        "event_id": event_id,
        "type": event_type,
        "campaign_id": campaign_id,
        "timestamp": _utcnow_iso(),
        "payload": payload,
    }

    serialized_event = json.dumps(event)

    list_key = f"{EVENT_LIST_PREFIX}{campaign_id}"
    redis_client.rpush(list_key, serialized_event)
    redis_client.expire(list_key, EVENT_TTL)

    channel_key = f"{PUB_SUB_PREFIX}{campaign_id}"
    redis_client.publish(channel_key, serialized_event)

    return event


def get_event_replay(campaign_id: str, last_event_id: int) -> list[dict]:
    """Returns every event for ``campaign_id`` with ``event_id > last_event_id`` (sync).

    Used by HTTP API callers and Celery tasks. The WebSocket handler uses
    :func:`aget_event_replay` to keep the event loop unblocked.
    """
    list_key = f"{EVENT_LIST_PREFIX}{campaign_id}"
    raw_events = redis_client.lrange(list_key, 0, -1)

    replayed_events: list[dict] = []
    for raw in raw_events:
        try:
            event = json.loads(raw)
            if event.get("event_id", 0) > last_event_id:
                replayed_events.append(event)
        except (json.JSONDecodeError, TypeError):
            continue

    return replayed_events


async def aemit_event(
    async_redis: aioredis.Redis,
    campaign_id: str,
    event_type: str,
    payload: dict,
) -> dict:
    """Async variant of :func:`emit_event` for use inside async handlers.

    Mirrors the sync version step-for-step: counter increment, list append
    with TTL, and pub/sub publish. The TTL extensions ensure the replay
    window tracks the most recent activity even when only async callers
    write to a campaign.
    """
    counter_key = f"{EVENT_COUNTER_PREFIX}{campaign_id}"
    event_id = await async_redis.incr(counter_key)
    await async_redis.expire(counter_key, EVENT_TTL)

    event = {
        "event_id": event_id,
        "type": event_type,
        "campaign_id": campaign_id,
        "timestamp": _utcnow_iso(),
        "payload": payload,
    }

    serialized_event = json.dumps(event)

    list_key = f"{EVENT_LIST_PREFIX}{campaign_id}"
    await async_redis.rpush(list_key, serialized_event)
    await async_redis.expire(list_key, EVENT_TTL)

    channel_key = f"{PUB_SUB_PREFIX}{campaign_id}"
    await async_redis.publish(channel_key, serialized_event)

    return event


async def aget_event_replay(
    async_redis: aioredis.Redis, campaign_id: str, last_event_id: int
) -> list[dict]:
    """Async variant of :func:`get_event_replay` for use inside async handlers."""
    list_key = f"{EVENT_LIST_PREFIX}{campaign_id}"
    raw_events = await async_redis.lrange(list_key, 0, -1)

    replayed_events: list[dict] = []
    for raw in raw_events:
        try:
            event = json.loads(raw)
            if event.get("event_id", 0) > last_event_id:
                replayed_events.append(event)
        except (json.JSONDecodeError, TypeError):
            continue

    return replayed_events


__all__ = [
    "EVENT_LIST_PREFIX",
    "EVENT_COUNTER_PREFIX",
    "EVENT_TTL",
    "PUB_SUB_PREFIX",
    "aemit_event",
    "aget_event_replay",
    "emit_event",
    "get_event_replay",
]
