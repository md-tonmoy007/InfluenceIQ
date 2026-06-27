"""Shared Apify actor runner for platform profile providers."""

from __future__ import annotations

from typing import Any

import httpx

from backend.core.config import settings


def actor_path(actor_id: str) -> str:
    return actor_id.replace("/", "~")


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
    for payload in payloads:
        try:
            response = httpx.post(
                endpoint,
                params={"token": settings.APIFY_API_TOKEN, "clean": "true"},
                json=payload,
                timeout=timeout,
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
