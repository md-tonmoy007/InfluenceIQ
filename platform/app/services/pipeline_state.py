from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import redis
import structlog

from app.config import settings

PIPELINE_EVENTS_TTL_SECONDS = 60 * 60
PIPELINE_STATE_TTL_SECONDS = 2 * 60 * 60

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def _state_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_STATE_DB)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _encode_hash_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, default=_json_default, sort_keys=True)


def emit_event(campaign_id: str, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Append a pipeline event and publish it to the campaign channel."""
    client = _state_redis()
    event_key = f"pipeline_events:{campaign_id}"
    sequence_key = f"pipeline_event_seq:{campaign_id}"
    channel = f"campaign:{campaign_id}"

    payload = payload or {}
    timestamp = datetime.now(UTC).isoformat()

    try:
        event_id = int(client.incr(sequence_key))
        event = {
            "event_id": event_id,
            "type": event_type,
            "campaign_id": campaign_id,
            "timestamp": timestamp,
            "payload": payload,
        }
        encoded = json.dumps(event, default=_json_default, sort_keys=True)
        pipe = client.pipeline()
        pipe.rpush(event_key, encoded)
        pipe.expire(event_key, PIPELINE_EVENTS_TTL_SECONDS)
        pipe.expire(sequence_key, PIPELINE_EVENTS_TTL_SECONDS)
        pipe.publish(channel, encoded)
        pipe.execute()
        return event
    except redis.RedisError as exc:
        logger.warning(
            "pipeline_event_write_failed",
            campaign_id=campaign_id,
            event_type=event_type,
            error=str(exc),
        )
        return {
            "event_id": 0,
            "type": event_type,
            "campaign_id": campaign_id,
            "timestamp": timestamp,
            "payload": payload,
        }


def update_state(campaign_id: str, **fields: Any) -> dict[str, str]:
    """Update the Redis hash used by REST and WebSocket status readers."""
    if not fields:
        return {}

    client = _state_redis()
    key = f"pipeline_state:{campaign_id}"
    encoded_fields = {name: _encode_hash_value(value) for name, value in fields.items()}

    try:
        pipe = client.pipeline()
        pipe.hset(key, mapping=encoded_fields)
        pipe.expire(key, PIPELINE_STATE_TTL_SECONDS)
        pipe.execute()
    except redis.RedisError as exc:
        logger.warning(
            "pipeline_state_write_failed",
            campaign_id=campaign_id,
            fields=sorted(fields),
            error=str(exc),
        )

    return encoded_fields
