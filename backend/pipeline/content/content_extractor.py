from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urljoin

from backend.pipeline.content.contracts import compact_number, platform_for_url

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^<]*(?:(?!</\1>)<[^<]*)*</\1>", re.IGNORECASE)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_RE = re.compile(
    r"<meta\s+(?:name|property)=[\"']([^\"']+)[\"']\s+content=[\"']([^\"']*)[\"'][^>]*>",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"href=[\"']([^\"']+)[\"']", re.IGNORECASE)
SOCIAL_RE = re.compile(
    r"https?://(?:www\.)?(?:instagram|youtube|youtu\.be|tiktok|x|twitter|facebook)\.com/[^\s\"'<>]+",
    re.IGNORECASE,
)
HANDLE_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{3,30})")
FOLLOWERS_RE = re.compile(r"(\d+(?:[.,]\d+)?\s*[KMB]?)\s+(?:followers|subscribers)", re.IGNORECASE)
ENGAGEMENT_RE = re.compile(r"(?:average\s+)?(?:likes|engagement|views)\s*[:\-]?\s*(\d+(?:[.,]\d+)?\s*[KMB]?)", re.IGNORECASE)
COMMENT_PREFIX_RE = re.compile(r"(?:comments?|recent comments?)\s*[:\-]\s*([^<.]+(?:\.[^<.]+){0,4})", re.IGNORECASE)


def _strip_html(raw_html: str) -> str:
    text = SCRIPT_STYLE_RE.sub(" ", raw_html)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _title(raw_html: str, url: str) -> str:
    match = TITLE_RE.search(raw_html)
    if match:
        return _strip_html(match.group(1))
    return url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()


def _metadata(raw_html: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for key, value in META_RE.findall(raw_html):
        metadata[key.lower()] = html.unescape(value).strip()
    return metadata


def _links(raw_html: str, base_url: str) -> list[str]:
    links = []
    for value in LINK_RE.findall(raw_html):
        if value.startswith("#") or value.lower().startswith("javascript:"):
            continue
        links.append(urljoin(base_url, html.unescape(value)))
    return sorted(set(links))


def _social_links(text: str, links: list[str]) -> list[str]:
    found = set(SOCIAL_RE.findall(text))
    found.update(link for link in links if platform_for_url(link) != "web")
    for handle in HANDLE_RE.findall(text):
        found.add(f"https://instagram.com/{handle}")
    return sorted(found)


def _comments(text: str) -> list[str]:
    comments: list[str] = []
    for block in COMMENT_PREFIX_RE.findall(text):
        comments.extend(part.strip(" .") for part in re.split(r"[.;]", block) if part.strip())
    if not comments:
        for quoted in re.findall(r"[\"“]([^\"”]{8,180})[\"”]", text):
            comments.append(quoted.strip())
    return comments[:50]


def _metrics(text: str) -> dict[str, Any]:
    followers = compact_number(FOLLOWERS_RE.search(text).group(1)) if FOLLOWERS_RE.search(text) else None
    engagement = compact_number(ENGAGEMENT_RE.search(text).group(1)) if ENGAGEMENT_RE.search(text) else None
    verified = bool(re.search(r"\bverified\b", text, re.IGNORECASE))
    return {
        "followers": followers,
        "average_engagement": engagement,
        "verified": verified,
    }


def _role5_candidate(content: dict[str, Any]) -> dict[str, Any]:
    text = str(content.get("content", ""))
    metrics = content["metrics"]
    return {
        "source_url": content["url"],
        "source_urls": [content["url"]],
        "bio": content["metadata"].get("description") or content["metadata"].get("og:description") or "",
        "content": text,
        "context": text[:4000],
        "comments": content["comments"],
        "followers": metrics.get("followers") or 0,
        "average_engagement": metrics.get("average_engagement") or 0,
        "verified": bool(metrics.get("verified")),
        "profile_urls": content["social_links"],
        "data_source_count": 1,
        "source_evidence": {
            "data_source_count": 1,
            "profile_url_available": bool(content["social_links"]),
            "metadata_completeness": round(
                sum(bool(content["metadata"].get(key)) for key in ("description", "og:description", "author")) / 3,
                2,
            ),
        },
        "raw_metrics": metrics,
    }


def extract_role5_content(page: dict) -> dict:
    url = str(page.get("url", ""))
    raw_html = str(page.get("html") or page.get("text") or "")
    text = _strip_html(raw_html)
    links = _links(raw_html, url)
    metadata = _metadata(raw_html)
    social_links = _social_links(" ".join([text, *links]), links)
    content = {
        "url": url,
        "title": _title(raw_html, url),
        "content": text,
        "social_links": social_links,
        "links": links[:100],
        "comments": _comments(text),
        "metrics": _metrics(text),
        "metadata": {
            **metadata,
            "status": page.get("status"),
            "cached": bool(page.get("cached", False)),
            "fetched_at": page.get("fetched_at"),
            "fetch_provider": page.get("provider"),
            "fetch_error": page.get("error"),
        },
        "provenance": {
            "source_url": url,
            "fetched_at": page.get("fetched_at"),
            "cached": bool(page.get("cached", False)),
            "status": page.get("status"),
        },
    }
    content["role5_candidate"] = _role5_candidate(content)
    content["role4_candidate"] = content["role5_candidate"]
    return content
