from __future__ import annotations

from datetime import datetime
import json
from app.services.redis_client import redis_client

EVENT_LIST_PREFIX = "pipeline_events:"
EVENT_COUNTER_PREFIX = "event_id_counter:"
PUB_SUB_PREFIX = "campaign:"
EVENT_TTL = 3600  # 1 hour


def emit_event(campaign_id: str, event_type: str, payload: dict) -> dict:
    """Publishes a structured workflow event to Redis pub/sub and appends it to the replay log."""
    # Increment event ID counter for this campaign
    counter_key = f"{EVENT_COUNTER_PREFIX}{campaign_id}"
    event_id = redis_client.incr(counter_key)
    redis_client.expire(counter_key, EVENT_TTL)

    # Construct structured event body
    event = {
        "event_id": event_id,
        "type": event_type,
        "campaign_id": campaign_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
    }

    # Serialize event
    serialized_event = json.dumps(event)

    # Append to event history list
    list_key = f"{EVENT_LIST_PREFIX}{campaign_id}"
    redis_client.rpush(list_key, serialized_event)
    redis_client.expire(list_key, EVENT_TTL)

    # Publish to pub/sub channel for active WebSocket connections
    channel_key = f"{PUB_SUB_PREFIX}{campaign_id}"
    redis_client.publish(channel_key, serialized_event)

    return event


def get_event_replay(campaign_id: str, last_event_id: int) -> list[dict]:
    """Retrieves all campaign events from the Redis log list that have an ID greater than last_event_id."""
    list_key = f"{EVENT_LIST_PREFIX}{campaign_id}"
    # Read entire list from Redis
    raw_events = redis_client.lrange(list_key, 0, -1)
    
    replayed_events = []
    for raw in raw_events:
        try:
            event = json.loads(raw)
            if event.get("event_id", 0) > last_event_id:
                replayed_events.append(event)
        except (json.JSONDecodeError, TypeError):
            continue

    return replayed_events
