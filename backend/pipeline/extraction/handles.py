from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PLATFORM_DOMAINS = {
    "instagram.com": "instagram", "x.com": "x", "twitter.com": "x",
    "tiktok.com": "tiktok", "youtube.com": "youtube", "youtu.be": "youtube",
    "facebook.com": "facebook", "fb.com": "facebook", "linkedin.com": "linkedin",
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
