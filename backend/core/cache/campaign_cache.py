from __future__ import annotations

from backend.core.cache.event_log import (
    EVENT_COUNTER_PREFIX,
    EVENT_LIST_PREFIX,
)
from backend.core.cache.redis_client import redis_client

STATE_KEY_PREFIX = "pipeline_state:"


def clear_campaign_pipeline_cache(campaign_id: str) -> None:
    """Remove all Redis keys for a campaign's live pipeline state and event replay."""
    keys = (
        f"{STATE_KEY_PREFIX}{campaign_id}",
        f"{EVENT_LIST_PREFIX}{campaign_id}",
        f"{EVENT_COUNTER_PREFIX}{campaign_id}",
    )
    redis_client.delete(*keys)


__all__ = ["STATE_KEY_PREFIX", "clear_campaign_pipeline_cache"]
