from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

SOCIAL_DOMAINS = {"youtube.com", "tiktok.com"}
PROFILE_KEYWORDS = {"about", "team", "contact", "author", "bio", "profile", "creators"}
BLOCKED_PATH_TOKENS = {
    "login",
    "signin",
    "signup",
    "register",
    "tag",
    "tags",
    "feed",
    "category",
    "page",
    "wp-json",
}
BLOCKED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
    ".xml",
    ".zip",
    ".mp4",
    ".mp3",
}
_HREF_RE = re.compile(r"""<a[^>]+href=["'](?P<href>[^"'#]+)["']""", flags=re.IGNORECASE)


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").casefold().removeprefix("www.").removeprefix("m.")


def _path_segments(url: str) -> list[str]:
    return [segment for segment in urlsplit(url).path.casefold().split("/") if segment]


def is_supported_social_profile(url: str) -> bool:
    host = _host(url)
    segments = _path_segments(url)
    if host == "youtube.com" and segments:
        return (
            segments[0].startswith("@")
            or (segments[0] == "channel" and len(segments) >= 2)
            or (segments[0] == "c" and len(segments) >= 2)
            or (segments[0] == "user" and len(segments) >= 2)
        )
    if host == "tiktok.com" and segments:
        return segments[0].startswith("@")
    return False


def is_social_domain(url: str) -> bool:
    return _host(url) in SOCIAL_DOMAINS


def is_same_domain_profile_page(parent_url: str, child_url: str) -> bool:
    if _host(parent_url) != _host(child_url):
        return False
    segments = _path_segments(child_url)
    return any(segment in PROFILE_KEYWORDS for segment in segments)


def should_follow_link(parent_url: str, child_url: str, *, depth: int, max_depth: int) -> bool:
    if depth >= max_depth:
        return False
    parsed = urlsplit(child_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.query and ("page=" in parsed.query.casefold() or "offset=" in parsed.query.casefold()):
        return False
    lowered = child_url.casefold()
    if any(lowered.endswith(extension) for extension in BLOCKED_EXTENSIONS):
        return False
    segments = _path_segments(child_url)
    if any(segment in BLOCKED_PATH_TOKENS for segment in segments):
        return False
    return is_supported_social_profile(child_url) or is_same_domain_profile_page(parent_url, child_url)


def select_discovered_links(html: str, base_url: str, *, depth: int, max_depth: int) -> list[str]:
    links: list[str] = []
    for match in _HREF_RE.finditer(html or ""):
        href = match.group("href").strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if should_follow_link(base_url, absolute, depth=depth, max_depth=max_depth):
            links.append(absolute)
    return list(dict.fromkeys(links))
