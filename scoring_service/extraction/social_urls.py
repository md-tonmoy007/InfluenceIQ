from __future__ import annotations

import re
from urllib.parse import urljoin

from .handles import normalize_profile_url, platform_for_url

URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)


def extract_social_urls(text: str = "", links: list[str] | None = None, base_url: str = "") -> dict[str, str]:
    profiles: dict[str, str] = {}
    for raw in [*URL_PATTERN.findall(text or ""), *(links or [])]:
        absolute = urljoin(base_url, str(raw).strip().rstrip(".,);]"))
        platform = platform_for_url(absolute)
        if platform and platform not in profiles:
            profiles[platform] = normalize_profile_url(absolute)
    return profiles


def profile_urls(profiles: dict[str, str]) -> list[str]:
    return list(dict.fromkeys(value for value in profiles.values() if str(value).startswith("http")))
