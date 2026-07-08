"""Shared Apify actor runner for platform profile providers."""

from __future__ import annotations

import time
from typing import Any

import httpx

from backend.core.config import settings

# Cap for a single Apify run-sync attempt. ``run_actor_sync`` tries several
# payload shapes; without a per-attempt cap one wrong-but-accepted payload can
# leave an actor running until the whole budget is spent. Bounded so a stuck
# attempt yields to the next candidate shape quickly.
_PER_ATTEMPT_TIMEOUT = 45.0


def actor_path(actor_id: str) -> str:
    return actor_id.replace("/", "~")


def _attempt_timeout(deadline: float) -> float | None:
    """Remaining time for the next payload attempt, or ``None`` if exhausted.

    ``timeout`` on the public helpers is a TOTAL wall-clock budget for the whole
    call (all payload shapes combined), not per attempt — otherwise trying N
    payload shapes at the full timeout could pin a worker for N×timeout seconds.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    return min(_PER_ATTEMPT_TIMEOUT, remaining)


def pick_first_item(items: Any, username: str | None = None) -> dict[str, Any] | None:
    if isinstance(items, dict):
        for key in ("items", "data", "results"):
            if isinstance(items.get(key), list):
                items = items[key]
                break
        else:
            return items if items else None
    if not isinstance(items, list):
        return None
    if username:
        lowered = username.lstrip("@").casefold()
        for item in items:
            if not isinstance(item, dict):
                continue
            for field in ("username", "handle", "userName", "uniqueId", "authorMeta"):
                raw = item.get(field)
                if isinstance(raw, dict):
                    raw = raw.get("uniqueId") or raw.get("name") or raw.get("nickName")
                raw_username = str(raw or "").lstrip("@").casefold()
                if raw_username == lowered:
                    return item
    first = items[0]
    return first if isinstance(first, dict) else None


def run_actor_sync(
    actor_id: str,
    payloads: list[dict[str, Any]],
    username: str | None = None,
    timeout: float = 120,
) -> dict[str, Any] | None:
    if not settings.APIFY_API_TOKEN:
        return None
    endpoint = f"https://api.apify.com/v2/acts/{actor_path(actor_id)}/run-sync-get-dataset-items"
    last_error: Exception | None = None
    deadline = time.monotonic() + timeout
    for payload in payloads:
        attempt_timeout = _attempt_timeout(deadline)
        if attempt_timeout is None:
            break
        try:
            response = httpx.post(
                endpoint,
                params={"token": settings.APIFY_API_TOKEN, "clean": "true"},
                json=payload,
                timeout=attempt_timeout,
            )
            response.raise_for_status()
            item = pick_first_item(response.json(), username)
            if item:
                return item
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return None


def _extract_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in ("items", "data", "results"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
        return [data] if data else []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def run_actor_sync_all(
    actor_id: str,
    payloads: list[dict[str, Any]],
    timeout: float = 180,
) -> list[dict[str, Any]]:
    """Run an Apify actor and return the full dataset (list of items).

    Comment scrapers return one item per comment, so the single-item
    ``run_actor_sync`` helper is not appropriate. This sibling returns
    every dict item in the dataset.
    """
    if not settings.APIFY_API_TOKEN:
        return []
    endpoint = f"https://api.apify.com/v2/acts/{actor_path(actor_id)}/run-sync-get-dataset-items"
    last_error: Exception | None = None
    deadline = time.monotonic() + timeout
    for payload in payloads:
        attempt_timeout = _attempt_timeout(deadline)
        if attempt_timeout is None:
            break
        try:
            response = httpx.post(
                endpoint,
                params={"token": settings.APIFY_API_TOKEN, "clean": "true"},
                json=payload,
                timeout=attempt_timeout,
            )
            response.raise_for_status()
            items = _extract_items(response.json())
            if items:
                return items
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return []


def profile_payloads(url: str, username: str, limit: int = 12) -> list[dict[str, Any]]:
    """Common Apify input shapes for single-profile scrapers."""
    handle = username.lstrip("@")
    return [
        {"usernames": [handle], "resultsLimit": 1},
        {"profiles": [handle], "resultsPerPage": limit},
        {"startUrls": [url], "resultsLimit": 1, "maxResults": limit},
        {"directUrls": [url], "resultsLimit": 1},
        {"twitterHandles": [handle], "maxItems": limit},
        {"handles": [handle], "maxItems": limit},
    ]
