"""Idempotency-Key support for write endpoints.

The Idempotency-Key pattern lets a client safely retry a non-idempotent
request (e.g. ``POST /api/campaigns`` which kicks off a long-running
pipeline). The first request stores the result in Redis under the key
for a bounded TTL; subsequent requests with the same key return the
stored result instead of re-running the side effects.

Storage shape::

    idempotency:{owner_id}:{key} -> JSON({
        "status_code": int,
        "body": dict,
        "created_at": ISO-8601,
    })

TTL is intentionally short (1 hour) — long enough for a normal retry
window, short enough that we never serve a stale "completed" response
to a brand-new request that happens to share the same random key.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.cache.redis_client import redis_client

log = logging.getLogger(__name__)

IDEMPOTENCY_PREFIX = "idempotency:"
IDEMPOTENCY_TTL = 3600  # 1 hour


def _key(owner_id: str, idempotency_key: str) -> str:
    return f"{IDEMPOTENCY_PREFIX}{owner_id}:{idempotency_key}"


def get_stored_response(owner_id: str, idempotency_key: str) -> dict[str, Any] | None:
    """Return the cached response for (owner, key) or ``None``."""
    if not owner_id or not idempotency_key:
        return None
    raw = redis_client.get(_key(owner_id, idempotency_key))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        log.warning(
            "Corrupt idempotency cache entry for key=%s owner=%s",
            idempotency_key,
            owner_id,
        )
        return None


def store_response(owner_id: str, idempotency_key: str, status_code: int, body: dict[str, Any]) -> None:
    """Cache the response for the (owner, key) pair with TTL."""
    if not owner_id or not idempotency_key:
        return
    payload = {
        "status_code": status_code,
        "body": body,
    }
    try:
        redis_client.set(
            _key(owner_id, idempotency_key),
            json.dumps(payload),
            ex=IDEMPOTENCY_TTL,
        )
    except Exception as exc:  # pragma: no cover
        log.warning(
            "Failed to store idempotency response for key=%s owner=%s: %s",
            idempotency_key,
            owner_id,
            exc,
        )


def clear_response(owner_id: str, idempotency_key: str) -> None:
    """Delete the cached response (used when the first attempt fails)."""
    if not owner_id or not idempotency_key:
        return
    try:
        redis_client.delete(_key(owner_id, idempotency_key))
    except Exception:  # pragma: no cover
        pass


__all__ = [
    "IDEMPOTENCY_PREFIX",
    "IDEMPOTENCY_TTL",
    "clear_response",
    "get_stored_response",
    "store_response",
]
