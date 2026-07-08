"""Platform enrichment persistence and orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import models
from backend.pipeline.content.contracts import normalize_url
from backend.pipeline.content.engagement_rollup import compute_recent_engagement
from backend.pipeline.content.providers.base import PlatformProfile, fetch_platform_profile
from backend.pipeline.content.providers.utils import handle_from_url
from backend.pipeline.extraction.handles import is_profile_url, platform_for_url

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
        post_row.post_url = str(
            post_data.get("url")
            or post_data.get("post_url")
            or (post_row.raw or {}).get("url")
            or (post_row.raw or {}).get("post_url")
            or (post_row.raw or {}).get("link")
            or post_row.post_url
            or ""
        )
        post_row.title = str(
            post_data.get("title")
            or (post_row.raw or {}).get("title")
            or post_row.title
            or ""
        )
        post_row.caption = str(
            post_data.get("caption")
            or post_data.get("description")
            or post_data.get("text")
            or (post_row.raw or {}).get("caption")
            or (post_row.raw or {}).get("description")
            or (post_row.raw or {}).get("text")
            or post_row.caption
            or ""
        )
        post_row.view_count = _int_or_none(
            post_data.get("view_count")
            or post_data.get("views")
            or (post_row.raw or {}).get("view_count")
            or (post_row.raw or {}).get("views")
        ) or post_row.view_count
        post_row.like_count = _int_or_none(
            post_data.get("like_count")
            or post_data.get("likes")
            or (post_row.raw or {}).get("like_count")
            or (post_row.raw or {}).get("likes")
        ) or post_row.like_count
        post_row.comment_count = _int_or_none(
            post_data.get("comment_count")
            or post_data.get("comments")
            or (post_row.raw or {}).get("comment_count")
            or (post_row.raw or {}).get("comments")
        ) or post_row.comment_count
        post_row.share_count = _int_or_none(
            post_data.get("share_count")
            or (post_row.raw or {}).get("share_count")
        ) or post_row.share_count
        post_row.fetch_provider = profile.provider
        post_row.raw = post_data
        post_row.fetched_at = now

        comments = post_data.get("comments")
        if isinstance(comments, list) and comments:
            _persist_raw_comments(session, post_row, comments, now, source=profile.provider)

    return row


def _is_legacy_caption_comment(row: models.PlatformComment) -> bool:
    """Detect caption-as-comment rows written before real comment fetching.

    Legacy rows were synthesized from post captions with no timestamp and
    no author hash, and their ``raw`` only contained ``{"text": ...}``.
    """
    return row.published_at is None and row.author_handle_hash is None


def persist_post_comments(
    session: Session,
    post_row: models.PlatformPost,
    raw_comments: list,
    *,
    source: str = "",
) -> int:
    """Persist real audience comments for a post, replacing legacy rows.

    ``raw_comments`` may be a list of :class:`RawComment` objects or plain
    dicts with the same fields. Author keys are hashed before storage and
    are not written to ``raw``.
    """
    if not raw_comments:
        return 0

    now = datetime.now(UTC)
    source_name = source or post_row.fetch_provider or "unknown"

    # Lazy migration: delete legacy caption-as-comment rows for this post.
    session.query(models.PlatformComment).filter(
        models.PlatformComment.platform_post_id == post_row.id,
        models.PlatformComment.published_at.is_(None),
        models.PlatformComment.author_handle_hash.is_(None),
    ).delete(synchronize_session=False)

    inserted = 0
    for comment in raw_comments[:MAX_COMMENTS_PER_POST]:
        if isinstance(comment, dict):
            text = str(comment.get("text") or comment.get("body") or "").strip()
            author = str(comment.get("author_key") or comment.get("author") or comment.get("author_handle") or "")
            like_count = _int_or_none(comment.get("like_count"))
            published_at = _parse_dt(comment.get("published_at"))
            external_id = str(comment.get("external_id") or comment.get("id") or "")
            reply_count = _int_or_none(comment.get("reply_count"))
        else:
            from backend.pipeline.content.providers.comments.base import RawComment

            if isinstance(comment, RawComment):
                text = comment.text.strip()
                author = comment.author_key
                like_count = comment.like_count
                published_at = comment.published_at
                external_id = comment.external_id
                reply_count = comment.reply_count
            else:
                continue

        if not text:
            continue
        if not external_id:
            external_id = f"{post_row.platform_post_id}:{inserted}"

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
        existing_comment.published_at = published_at
        existing_comment.fetched_at = now
        existing_comment.raw = {
            "source": source_name,
            "reply_count": reply_count,
        }
        inserted += 1

    return inserted


def _persist_raw_comments(
    session: Session,
    post_row: models.PlatformPost,
    comments: list,
    now: datetime,
    source: str,
) -> None:
    """Backward-compatible helper used when a provider supplies comments inline."""
    persist_post_comments(session, post_row, comments, source=source)


def _parse_dt(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


_GENERIC_GARBAGE_FRAGMENTS = (
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
)


def _is_garbage_url(url: str) -> bool:
    lower = url.lower()
    if any(fragment in lower for fragment in _GENERIC_GARBAGE_FRAGMENTS):
        return True
    platform = platform_for_url(url)
    if platform in {"tiktok", "youtube"}:
        return not is_profile_url(url)
    return False


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
    """Fetch platform profiles via HTTP — call this OUTSIDE any DB session.

    Bounded by ``ENRICH_PROFILE_FETCH_BUDGET_SEC`` total wall-clock: once the
    budget is spent, remaining URLs are skipped (returned with no profile)
    rather than fetched, so a single influencer with many URLs cannot pin a
    worker slot and stall the scraping queue.
    """
    results: list[tuple[str, PlatformProfile | None]] = []
    deadline = time.monotonic() + settings.ENRICH_PROFILE_FETCH_BUDGET_SEC
    for url in urls:
        if time.monotonic() >= deadline:
            log.warning("fetch_profiles_for_urls: budget exhausted, skipping url=%s", url)
            results.append((url, None))
            continue
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
    best_avg_views = influencer.avg_views or 0
    best_engagement_rate = influencer.engagement_rate or 0.0
    best_lifetime_views = 0
    primary_platform = influencer.primary_platform

    # Sort by (platform, profile_url) — the columns of uq_platform_profiles_platform_url —
    # so concurrent tasks that touch overlapping profile rows always acquire row locks in
    # the same global order. Without this, two tasks upserting the same URLs in different
    # orders can each hold one row and wait on the other, deadlocking in Postgres.
    ordered = sorted(
        fetched,
        key=lambda item: (item[1].platform, item[1].url) if item[1] is not None else ("", item[0]),
    )

    for url, profile in ordered:
        if profile is None:
            failed += 1
            coverage[url] = "unsupported"
            continue
        try:
            with session.begin_nested():
                db_profile = persist_platform_profile(session, influencer_id, profile)
                session.flush()
            enriched += 1
            coverage[url] = "partial" if profile.error else "ok"
        except (IntegrityError, DataError) as exc:
            log.warning("persist_platform_profile: skipped url=%s influencer=%s reason=%s", url, influencer_id, exc.__class__.__name__)
            coverage[url] = "duplicate" if isinstance(exc, IntegrityError) else "error"
            continue

        rollup = compute_recent_engagement(profile)
        recent_views = rollup.get("recent_views")
        recent_engagement_rate = rollup.get("recent_engagement_rate")
        lifetime_views = rollup.get("lifetime_views")

        if recent_views is not None:
            db_profile.avg_engagement = _clamp_int(recent_views)
        if recent_engagement_rate is not None:
            db_profile.engagement_rate = float(recent_engagement_rate)

        if profile.followers and profile.followers > best_followers:
            best_followers = profile.followers
            primary_platform = profile.platform
        if recent_views is not None and recent_views > best_avg_views:
            best_avg_views = recent_views
        if recent_engagement_rate is not None and recent_engagement_rate > best_engagement_rate:
            best_engagement_rate = recent_engagement_rate
        if lifetime_views is not None and lifetime_views > best_lifetime_views:
            best_lifetime_views = lifetime_views

    influencer.follower_count = _clamp_int(best_followers) or influencer.follower_count
    if best_avg_views > 0:
        influencer.avg_views = _clamp_int(best_avg_views)
    elif best_lifetime_views > 0:
        influencer.avg_views = _clamp_int(best_lifetime_views)
    influencer.engagement_rate = best_engagement_rate or influencer.engagement_rate
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
_EMBEDDING_CORPUS_CAP = 8_000


def _build_profile_corpus(profile: PlatformProfile) -> str:
    parts: list[str] = []
    if profile.name:
        parts.append(profile.name)
    if profile.bio:
        parts.append(profile.bio)
    for post in (profile.posts or [])[:12]:
        for key in ("caption", "title", "description"):
            value = post.get(key)
            if value and isinstance(value, str):
                parts.append(str(value))
    return " ".join(parts)[:_EMBEDDING_CORPUS_CAP]


def _build_influencer_embedding_text(session: Session, influencer_id: UUID) -> str | None:
    profiles = (
        session.query(models.PlatformProfile)
        .filter(models.PlatformProfile.influencer_id == influencer_id)
        .all()
    )
    if not profiles:
        return None
    parts: list[str] = []
    for pr in profiles:
        if pr.bio:
            parts.append(pr.bio)
        if pr.display_name:
            parts.append(pr.display_name)
    return " ".join(parts)[:_EMBEDDING_CORPUS_CAP] or None


def compute_and_persist_embedding(
    session: Session,
    influencer_id: UUID,
) -> dict[str, Any] | None:
    """Compute a relevance embedding for *influencer_id* and store it.

    Returns the embedding envelope dict on success, ``None`` when the
    embedding backend is unavailable, and *always* writes a JSONB
    envelope to ``influencer.embedding`` so the relevance scorer can
    detect both sides are present. The ``source`` field is
    ``"openrouter"`` for both live OpenRouter vectors and deterministic
    hash-derived stub vectors; the stub vs live distinction is implicit
    (the value lives only in the underlying vector).
    """
    influencer = session.get(models.Influencer, influencer_id)
    if influencer is None:
        return None

    corpus = _build_influencer_embedding_text(session, influencer_id)
    if not corpus:
        return None

    try:
        from backend.ml.models.registry import registry as model_registry

        reg = model_registry()
        backend = reg.get(reg.resolve_name("embedding"))
        embed_fn = getattr(backend, "embed_text", None)
        if embed_fn is None:
            return None

        result = embed_fn(corpus)
        if inspect.isawaitable(result):
            result = asyncio.run(result)

        vector = result if isinstance(result, list) else None
        if not vector:
            return None

        envelope: dict[str, Any] = {
            "source": "openrouter",
            "model": _embedding_model_name(),
            "vector": vector,
        }
    except Exception:
        log.exception("compute_and_persist_embedding failed for %s", influencer_id)
        envelope = {
            "source": "openrouter",
            "model": _embedding_model_name(),
            "vector": _stub_vector(corpus),
        }

    influencer.embedding = envelope
    influencer.updated_at = datetime.now(UTC)
    return envelope


def compute_and_persist_campaign_embedding(
    session: Session,
    campaign_id: UUID,
) -> dict[str, Any] | None:
    """Compute a relevance embedding for *campaign_id* and store it."""
    campaign = session.get(models.Campaign, campaign_id)
    if campaign is None:
        return None

    parts: list[str] = []
    for field in ("niche", "target_audience", "goals", "product", "search_query"):
        value = getattr(campaign, field, None)
        if value and isinstance(value, str):
            parts.append(str(value))
    corpus = " ".join(parts)[:_EMBEDDING_CORPUS_CAP]
    if not corpus:
        return None

    try:
        from backend.ml.models.registry import registry as model_registry

        reg = model_registry()
        backend = reg.get(reg.resolve_name("embedding"))
        embed_fn = getattr(backend, "embed_text", None)
        if embed_fn is None:
            return None

        result = embed_fn(corpus)
        if inspect.isawaitable(result):
            result = asyncio.run(result)

        vector = result if isinstance(result, list) else None
        if not vector:
            return None

        envelope: dict[str, Any] = {
            "source": "openrouter",
            "model": _embedding_model_name(),
            "vector": vector,
        }
    except Exception:
        log.exception("compute_and_persist_campaign_embedding failed for %s", campaign_id)
        envelope = {
            "source": "openrouter",
            "model": _embedding_model_name(),
            "vector": _stub_vector(corpus),
        }

    campaign.embedding = envelope
    return envelope


def _embedding_model_name() -> str:
    import os

    return os.environ.get("UMGL_EMBEDDING_MODEL", "text-embedding-3-small")


def _stub_vector(text: str) -> list[float]:
    import os

    dim = int(os.environ.get("EMBEDDING_DIM", "1536"))
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [b / 255.0 for b in digest]
    expanded: list[float] = []
    while len(expanded) < dim:
        expanded.extend(raw)
    vec = expanded[:dim]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


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
