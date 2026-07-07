from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PLATFORM_DOMAINS = {
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube", "youtu.be": "youtube",
}
TRACKING_PARAMETERS = {"fbclid", "gclid", "igshid", "ref", "ref_src", "si", "lang"}
HANDLE_PATTERN = re.compile(r"(?<![\w@])@([A-Za-z0-9._-]{2,50})")


def extract_handles(text: str) -> list[str]:
    return list(dict.fromkeys(f"@{match}" for match in HANDLE_PATTERN.findall(text or "")))


def _ensure_scheme(value: str) -> str:
    value = value.strip()
    if value.startswith("//"):
        return "https:" + value
    return value if "://" in value else "https://" + value


def platform_for_url(url: str) -> str | None:
    host = urlsplit(_ensure_scheme(url)).hostname or ""
    return PLATFORM_DOMAINS.get(host.casefold().removeprefix("www.").removeprefix("m."))


def normalize_profile_url(url: str) -> str:
    if not str(url).strip():
        return ""
    parts = urlsplit(_ensure_scheme(str(url)))
    host = (parts.hostname or "").casefold().removeprefix("www.").removeprefix("m.")
    host = {"twitter.com": "x.com", "fb.com": "facebook.com"}.get(host, host)
    path = re.sub(r"/+", "/", parts.path).rstrip("/")
    if host == "youtu.be" and path:
        host, path = "youtube.com", f"/watch/{path.lstrip('/')}"
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                       if key.casefold() not in TRACKING_PARAMETERS and not key.casefold().startswith("utm_")])
    return urlunsplit(("https", host, path, query, ""))


_PROFILE_PATH_PATTERNS: dict[str, re.Pattern[str]] = {
    "tiktok": re.compile(r"^/@[\w.\-]{1,50}/?$"),
    "youtube": re.compile(
        r"^/(@[\w.\-]{1,50}|channel/[\w-]{1,64}|c/[\w.\-]{1,64}|user/[\w.\-]{1,64})/?$"
    ),
}

_INSTAGRAM_RESERVED_PATHS = {
    "p", "reel", "reels", "tv", "stories", "explore", "accounts",
    "direct", "about", "developer", "legal", "privacy", "web", "api",
}

_INSTAGRAM_USERNAME_RE = re.compile(r"^[\w.]{1,30}$")

_WWW_PREFIXED_HOSTS = {"tiktok.com", "youtube.com"}


def _is_instagram_profile_path(path: str) -> bool:
    segments = [s for s in path.split("/") if s]
    if len(segments) != 1 or segments[0].casefold() in _INSTAGRAM_RESERVED_PATHS:
        return False
    return bool(_INSTAGRAM_USERNAME_RE.match(segments[0]))


def is_profile_url(url: str) -> bool:
    platform = platform_for_url(url)
    if platform is None:
        return False
    if platform == "instagram":
        path = urlsplit(_ensure_scheme(url)).path or "/"
        return _is_instagram_profile_path(path)
    pattern = _PROFILE_PATH_PATTERNS.get(platform)
    if pattern is None:
        return True
    path = urlsplit(_ensure_scheme(url)).path or "/"
    return bool(pattern.match(path))


def canonical_profile_url(url: str) -> str | None:
    if not is_profile_url(url):
        return None
    normalized = normalize_profile_url(url)
    parts = urlsplit(normalized)
    host = parts.netloc
    if host in _WWW_PREFIXED_HOSTS:
        host = f"www.{host}"
    return urlunsplit(("https", host, parts.path, "", ""))


def username_from_profile(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("@"):
        return raw[1:].casefold()
    if not raw:
        return ""
    parts = urlsplit(normalize_profile_url(raw))
    segments = [segment for segment in parts.path.split("/") if segment]
    if not segments:
        return ""
    ignored = {"channel", "c", "user", "watch", "pages", "profile.php"}
    candidate = segments[-1] if segments[0].casefold() in ignored and len(segments) > 1 else segments[0]
    return candidate.removeprefix("@").casefold()


def username_stems(candidate: dict) -> set[str]:
    values = [str(candidate.get("handle") or ""), *(str(v) for v in (candidate.get("platforms") or {}).values()),
              *(str(v) for v in candidate.get("profile_urls", []) or [])]
    return {username for value in values if (username := username_from_profile(value))}
