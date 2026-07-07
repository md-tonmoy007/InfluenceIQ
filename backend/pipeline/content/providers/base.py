from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from backend.pipeline.content.contracts import CrawlPage, platform_for_url


@dataclass
class PlatformProfile:
    platform: str
    url: str
    handle: str = ""
    name: str = ""
    bio: str = ""
    followers: int | None = None
    following: int | None = None
    average_engagement: int | None = None
    verified: bool = False
    profile_urls: list[str] = field(default_factory=list)
    posts: list[dict[str, Any]] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    provider: str = "platform"
    error: str | None = None
    coverage: dict[str, Any] = field(default_factory=dict)

    def to_html(self) -> str:
        profile_links = "".join(f"<a href='{url}'>{url}</a>" for url in self.profile_urls)
        posts = " ".join(
            " ".join(str(post.get(key, "")) for key in ("title", "caption", "description", "text"))
            for post in self.posts[:12]
        )
        comments = ". ".join(comment for comment in self.comments[:50] if comment)
        metrics = " ".join(
            part
            for part in (
                f"{self.followers} followers" if self.followers is not None else "",
                f"{self.following} following" if self.following is not None else "",
                f"Average engagement: {self.average_engagement}" if self.average_engagement is not None else "",
                "Verified" if self.verified else "",
            )
            if part
        )
        return (
            "<html><head>"
            f"<title>{self.name or self.handle or self.platform} profile</title>"
            f"<meta name='description' content='{_escape_attr(self.bio)}'>"
            "</head><body>"
            f"<h1>{_escape_text(self.name or self.handle)}</h1>"
            f"<p>@{_escape_text(self.handle.lstrip('@'))}</p>"
            f"<p>{_escape_text(self.bio)}</p>"
            f"<p>{_escape_text(metrics)}</p>"
            f"<p>Comments: {_escape_text(comments)}</p>"
            f"<p>{_escape_text(posts)}</p>"
            f"{profile_links}"
            "</body></html>"
        )

    def to_page(self) -> dict[str, Any]:
        return CrawlPage(
            url=self.url,
            status=200 if self.error is None else 599,
            html=self.to_html(),
            fetched_at=datetime.now(UTC).isoformat(),
            cached=False,
            provider=self.provider,
            error=self.error,
        ).to_dict()


def _escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(value: str) -> str:
    return _escape_text(value).replace("'", "&#39;").replace('"', "&quot;")


def fetch_platform_profile(url: str) -> dict[str, Any] | None:
    platform = platform_for_url(url)
    providers: dict[str, Callable[[str], PlatformProfile | None]] = {}

    if platform == "youtube":
        from backend.pipeline.content.providers.youtube import fetch_youtube_profile

        providers[platform] = fetch_youtube_profile
    elif platform == "instagram":
        from backend.pipeline.content.providers.instagram import fetch_instagram_profile

        providers[platform] = fetch_instagram_profile
    elif platform == "tiktok":
        from backend.pipeline.content.providers.tiktok import fetch_tiktok_profile

        providers[platform] = fetch_tiktok_profile

    provider = providers.get(platform)
    if provider is None:
        return None
    profile = provider(url)
    if profile is None:
        return None
    return profile.to_page()
