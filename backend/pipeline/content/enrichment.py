"""Platform enrichment persistence and orchestration."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from backend.core.database import models
from backend.pipeline.content.providers.base import PlatformProfile, fetch_platform_profile
from backend.pipeline.content.providers.utils import handle_from_url
from backend.pipeline.content.contracts import normalize_url, platform_for_url

log = logging.getLogger(__name__)

MAX_COMMENTS_PER_POST = 200
MAX_POSTS_PER_PROFILE = 20


def _hash_author(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def collect_platform_urls(influencer: models.Influencer, crawl_sources: list[models.CrawlSource] | None = None) -> list[str]:
    """Collect normalized social profile URLs for an influencer."""
    urls: list[str] = []
    seen: set[str] = set()
    for value in (influencer.platforms or {}).values():
        if isinstance(value, str) and value.startswith("http"):
            normalized = normalize_url(value)
            if normalized not in seen:
                seen.add(normalized)
                urls.append(normalized)
    if crawl_sources:
        import re

        pattern = re.compile(
            r"https?://(?:www\.)?(?:instagram|youtube|youtu\.be|tiktok|x|twitter)\.com/[^\s\"'<>]+",
            flags=re.IGNORECASE,
        )
        for source in crawl_sources:
            for blob in (source.content or "", source.html or ""):
                for match in pattern.findall(blob):
                    normalized = normalize_url(match)
                    if normalized not in seen:
                        seen.add(normalized)
                        urls.append(normalized)
    return urls


def _profile_from_page(url: str) -> PlatformProfile | None:
    page = fetch_platform_profile(url)
    if page is None:
        return None
    return PlatformProfile(
        platform=platform_for_url(url) or "unknown",
        url=url,
        handle=handle_from_url(url),
        name=page.get("title") or handle_from_url(url),
        bio="",
        profile_urls=[url],
        provider=page.get("provider") or "fetcher",
        error=page.get("error"),
    )


def fetch_platform_profile_data(url: str) -> PlatformProfile | None:
    """Fetch a structured platform profile using the provider registry."""
    normalized = normalize_url(url)
    platform = platform_for_url(normalized)
    if not platform:
        return None
    try:
        if platform == "youtube":
            from backend.pipeline.content.providers.youtube import fetch_youtube_profile

            return fetch_youtube_profile(normalized)
        if platform == "instagram":
            from backend.pipeline.content.providers.instagram import fetch_instagram_profile

            return fetch_instagram_profile(normalized)
        if platform == "tiktok":
            from backend.pipeline.content.providers.tiktok import fetch_tiktok_profile

            return fetch_tiktok_profile(normalized)
        if platform == "x":
            from backend.pipeline.content.providers.x import fetch_x_profile

            return fetch_x_profile(normalized)
    except Exception as exc:
        log.warning("fetch_platform_profile_data failed for %s: %s", normalized, exc)
    return _profile_from_page(normalized)


def persist_platform_profile(
    session: Session,
    influencer_id: UUID,
    profile: PlatformProfile,
) -> models.PlatformProfile:
    """Upsert a platform profile and its posts/comments."""
    now = datetime.now(UTC)
    account_id = str((profile.raw or {}).get("channel_id") or profile.handle or profile.url)
    # Look up by (platform, profile_url) — matches the unique constraint.
    # A profile URL belongs to one canonical row regardless of which influencer
    # triggered the fetch, so we update the existing row rather than creating a
    # duplicate that would violate uq_platform_profiles_platform_url.
    row = (
        session.query(models.PlatformProfile)
        .filter(
            models.PlatformProfile.platform == profile.platform,
            models.PlatformProfile.profile_url == profile.url,
        )
        .first()
    )
    if row is None:
        row = models.PlatformProfile(
            id=uuid4(),
            influencer_id=influencer_id,
            platform=profile.platform,
            profile_url=profile.url,
        )
        session.add(row)

    row.platform_account_id = account_id
    row.handle = profile.handle
    row.display_name = profile.name
    row.bio = profile.bio
    row.followers = _clamp_int(profile.followers)
    row.following = _clamp_int(profile.following)
    row.avg_engagement = _clamp_int(profile.average_engagement)
    row.verified = bool(profile.verified)
    row.fetch_provider = profile.provider
    row.fetch_status = "partial" if profile.error else "ok"
    row.raw = profile.raw or {}
    row.fetched_at = now
    row.updated_at = now

    for post_data in profile.posts[:MAX_POSTS_PER_PROFILE]:
        post_id = str(post_data.get("id") or post_data.get("platform_post_id") or uuid4())
        post_row = (
            session.query(models.PlatformPost)
            .filter(
                models.PlatformPost.platform_profile_id == row.id,
                models.PlatformPost.platform_post_id == post_id,
            )
            .first()
        )
        if post_row is None:
            post_row = models.PlatformPost(
                id=uuid4(),
                platform_profile_id=row.id,
                platform=profile.platform,
                platform_post_id=post_id,
            )
            session.add(post_row)
        post_row.post_url = str(post_data.get("url") or post_data.get("post_url") or "")
        post_row.title = str(post_data.get("title") or "")
        post_row.caption = str(post_data.get("caption") or post_data.get("description") or post_data.get("text") or "")
        post_row.view_count = _int_or_none(post_data.get("view_count") or post_data.get("views"))
        post_row.like_count = _int_or_none(post_data.get("like_count") or post_data.get("likes"))
        post_row.comment_count = _int_or_none(post_data.get("comment_count") or post_data.get("comments"))
        post_row.share_count = _int_or_none(post_data.get("share_count"))
        post_row.fetch_provider = profile.provider
        post_row.raw = post_data
        post_row.fetched_at = now

        comments = post_data.get("comments")
        if isinstance(comments, list) and comments:
            comment_texts = comments
        elif profile.comments:
            comment_texts = profile.comments
        else:
            comment_texts = []
        for index, comment in enumerate(comment_texts[:MAX_COMMENTS_PER_POST]):
            if isinstance(comment, dict):
                text = str(comment.get("text") or comment.get("body") or "")
                author = str(comment.get("author") or comment.get("author_handle") or "")
                like_count = _int_or_none(comment.get("like_count"))
                external_id = str(comment.get("id") or f"{post_id}:{index}")
            else:
                text = str(comment)
                author = ""
                like_count = None
                external_id = f"{post_id}:{index}"
            if not text.strip():
                continue
            existing_comment = (
                session.query(models.PlatformComment)
                .filter(
                    models.PlatformComment.platform_post_id == post_row.id,
                    models.PlatformComment.platform_comment_id == external_id,
                )
                .first()
            )
            if existing_comment is None:
                existing_comment = models.PlatformComment(
                    id=uuid4(),
                    platform_post_id=post_row.id,
                    platform_comment_id=external_id,
                    text=text,
                )
                session.add(existing_comment)
            existing_comment.author_handle_hash = _hash_author(author) if author else None
            existing_comment.like_count = like_count
            existing_comment.fetched_at = now
            existing_comment.raw = comment if isinstance(comment, dict) else {"text": text}

    return row


_GARBAGE_URL_FRAGMENTS = (
    "/intent/tweet",
    "/intent/retweet",
    "/intent/like",
    "/share?",
    "/sharer/",
    "addthis.com",
    "pinterest.com/pin/create",
    "reddit.com/submit",
    "linkedin.com/shareArticle",
    "t.me/share",
    "youtube.com/watch",   # video page, not a channel
    "youtu.be/",           # shortened video link
    "youtube.com/shorts/", # YouTube Shorts
)


def _is_garbage_url(url: str) -> bool:
    """Return True for share-button / intent URLs that are not real profiles."""
    lower = url.lower()
    return any(fragment in lower for fragment in _GARBAGE_URL_FRAGMENTS)


def collect_platform_urls_for_influencer(
    session: Session,
    influencer_id: UUID,
    crawl_sources: list[models.CrawlSource] | None = None,
) -> list[str]:
    """Return non-garbage platform URLs for an influencer (brief DB read)."""
    influencer = session.get(models.Influencer, influencer_id)
    if influencer is None:
        return []
    urls = collect_platform_urls(influencer, crawl_sources)
    return [u for u in urls if not _is_garbage_url(u)]


def fetch_profiles_for_urls(urls: list[str]) -> list[tuple[str, PlatformProfile | None]]:
    """Fetch platform profiles via HTTP — call this OUTSIDE any DB session."""
    results = []
    for url in urls:
        profile = fetch_platform_profile_data(url)
        results.append((url, profile))
    return results


def persist_enrichment(
    session: Session,
    influencer_id: UUID,
    fetched: list[tuple[str, PlatformProfile | None]],
) -> dict[str, Any]:
    """Persist pre-fetched platform profiles and update the influencer row."""
    influencer = session.get(models.Influencer, influencer_id)
    if influencer is None:
        return {"status": "missing", "profiles": 0}

    enriched = 0
    failed = 0
    coverage: dict[str, str] = {}
    best_followers = influencer.follower_count or 0
    best_engagement = influencer.engagement_rate or 0.0
    primary_platform = influencer.primary_platform

    for url, profile in fetched:
        if profile is None:
            failed += 1
            coverage[url] = "unsupported"
            continue
        try:
            with session.begin_nested():
                persist_platform_profile(session, influencer_id, profile)
                session.flush()
            enriched += 1
            coverage[url] = "partial" if profile.error else "ok"
        except (IntegrityError, DataError) as exc:
            log.warning("persist_platform_profile: skipped url=%s influencer=%s reason=%s", url, influencer_id, exc.__class__.__name__)
            coverage[url] = "duplicate" if isinstance(exc, IntegrityError) else "error"
            continue
        if profile.followers and profile.followers > best_followers:
            best_followers = profile.followers
            primary_platform = profile.platform
        if profile.average_engagement:
            best_engagement = float(profile.average_engagement)

    influencer.follower_count = _clamp_int(best_followers) or influencer.follower_count
    influencer.engagement_rate = best_engagement or influencer.engagement_rate
    influencer.primary_platform = primary_platform or influencer.primary_platform
    influencer.updated_at = datetime.now(UTC)

    return {
        "status": "ok" if enriched else "partial",
        "profiles": enriched,
        "failed": failed,
        "coverage": coverage,
    }


def enrich_influencer_platforms(
    session: Session,
    influencer_id: UUID,
    *,
    crawl_sources: list[models.CrawlSource] | None = None,
) -> dict[str, Any]:
    """Fetch and persist all known platform profiles for an influencer.

    Prefer calling collect_platform_urls_for_influencer + fetch_profiles_for_urls
    + persist_enrichment separately from the task so HTTP requests don't hold
    an open DB transaction.  This wrapper exists for callers that don't need
    that separation.
    """
    influencer = session.get(models.Influencer, influencer_id)
    if influencer is None:
        return {"status": "missing", "profiles": 0}
    urls = [u for u in collect_platform_urls(influencer, crawl_sources) if not _is_garbage_url(u)]
    fetched = fetch_profiles_for_urls(urls)
    return persist_enrichment(session, influencer_id, fetched)


_PG_INT_MAX = 2_147_483_647


def _clamp_int(value: Any) -> int | None:
    """Convert to int and clamp to PostgreSQL INTEGER range."""
    if value is None:
        return None
    try:
        return min(int(value), _PG_INT_MAX)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
