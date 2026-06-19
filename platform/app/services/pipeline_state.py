from __future__ import annotations

from app.services.redis_client import redis_client

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
    # HSET fields
    redis_client.hset(key, mapping=initial_state)
    # Set expiration to 2 hours
    redis_client.expire(key, STATE_TTL)


def update_pipeline_state(campaign_id: str, **fields) -> None:
    """Updates fields in the pipeline state hash and extends/renews its TTL."""
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    # Convert all values to string for redis storage
    mapping = {k: str(v) for k, v in fields.items()}
    if mapping:
        redis_client.hset(key, mapping=mapping)
    redis_client.expire(key, STATE_TTL)


def get_pipeline_state(campaign_id: str) -> dict | None:
    """Retrieves and normalizes the pipeline state from Redis.
    Casts numeric fields to int and returns a dictionary.
    """
    key = f"{STATE_KEY_PREFIX}{campaign_id}"
    state = redis_client.hgetall(key)
    if not state:
        return None

    # Cast integer columns to int
    int_cols = [
        "urls_discovered",
        "urls_scraped",
        "urls_failed",
        "influencers_found",
        "scores_computed",
    ]
    for col in int_cols:
        if col in state:
            try:
                state[col] = int(state[col])
            except ValueError:
                state[col] = 0

    return state
