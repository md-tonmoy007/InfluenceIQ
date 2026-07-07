from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from backend.pipeline.extraction.handles import platform_for_url as _canonical_platform_for_url


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    relevance_score: float = 0.0
    provider: str = "fallback"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": round(float(self.relevance_score), 2),
            "provider": self.provider,
        }


@dataclass
class CrawlPage:
    url: str
    status: int
    html: str = ""
    text: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    cached: bool = False
    provider: str = "httpx"
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "html": self.html,
            "text": self.text,
            "fetched_at": self.fetched_at,
            "cached": self.cached,
            "provider": self.provider,
            "error": self.error,
            "headers": self.headers,
        }


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+$", "", parsed.path or "")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{host}{path}{query}"


def url_cache_key(url: str) -> str:
    digest = hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()
    return f"url_cache:{digest}"


def domain_for_url(url: str) -> str:
    return urlparse(normalize_url(url)).netloc.lower().removeprefix("www.")


def platform_for_url(url: str) -> str:
    return _canonical_platform_for_url(url) or "web"


def compact_number(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    cleaned = value.strip().replace(",", "").upper()
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KMB])?", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
    return int(number * multiplier)
