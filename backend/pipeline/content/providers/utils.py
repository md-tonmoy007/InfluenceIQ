from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote, urlparse


def first_path_part(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return unquote(path.split("/", 1)[0]) if path else ""


def handle_from_url(url: str) -> str:
    handle = first_path_part(url)
    if handle in {"channel", "c", "user", "shorts", "watch", "results", "explore", "p", "playlist", "embed", "live"}:
        parts = urlparse(url).path.strip("/").split("/")
        return unquote(parts[1]) if len(parts) > 1 else ""
    return handle.lstrip("@")


def json_ld_blocks(html: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for match in re.finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            blocks.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            blocks.append(payload)
    return blocks


def meta_content(html: str, key: str) -> str:
    patterns = [
        rf"<meta\s+name=[\"']{re.escape(key)}[\"']\s+content=[\"']([^\"']*)[\"']",
        rf"<meta\s+property=[\"']{re.escape(key)}[\"']\s+content=[\"']([^\"']*)[\"']",
        rf"<meta\s+content=[\"']([^\"']*)[\"']\s+(?:name|property)=[\"']{re.escape(key)}[\"']",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def find_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).replace(",", "")
    try:
        return int(float(value))
    except ValueError:
        return None


def compact_text_number(value: str) -> int | None:
    cleaned = value.replace(",", "").strip().upper()
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KMB])?", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(match.group(2), 1)
    return int(number * multiplier)
