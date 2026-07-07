"""Build influencer candidate payloads for scoring and deep analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from backend.core.database import models
from backend.pipeline.extraction.handles import is_profile_url
from sqlalchemy.orm import Session


def build_influencer_candidate(
    session: Session,
    influencer_id: UUID,
    campaign_id: UUID,
    *,
    include_platform: bool = True,
    comment_limit: int = 500,
) -> dict[str, Any]:
    """Single source of truth for scoring candidate assembly."""
    influencer = session.get(models.Influencer, influencer_id)
    if influencer is None:
        return {}

    mentions = list(influencer.mentions or [])
    platforms = dict(influencer.platforms or {})
    profile_urls = [value for value in platforms.values() if isinstance(value, str) and is_profile_url(value)]
    sources = _sources_summary(session, influencer_id, campaign_id)
    source_urls = [row["url"] for row in sources]

    comments: list[str] = []
    followers = int(influencer.follower_count or 0)
    average_engagement = int(influencer.avg_views or 0)
    engagement_rate = float(influencer.engagement_rate or 0.0)
    verified = False
    bio_parts: list[str] = []
    titles: list[str] = []
    credentials = list(influencer.credentials or [])
    profiles: list[models.PlatformProfile] = []

    if include_platform:
        profiles = (
            session.query(models.PlatformProfile)
            .filter(models.PlatformProfile.influencer_id == influencer_id)
            .all()
        )
        for profile in profiles:
            if profile.bio:
                bio_parts.append(profile.bio)
            if profile.followers and profile.followers > followers:
                followers = profile.followers
            if profile.avg_engagement and profile.avg_engagement > average_engagement:
                average_engagement = profile.avg_engagement
            if profile.engagement_rate and profile.engagement_rate > engagement_rate:
                engagement_rate = profile.engagement_rate
            verified = verified or bool(profile.verified)
            posts = (
                session.query(models.PlatformPost)
                .filter(models.PlatformPost.platform_profile_id == profile.id)
                .order_by(models.PlatformPost.published_at.desc().nullslast())
                .limit(20)
                .all()
            )
            for post in posts:
                if post.caption:
                    bio_parts.append(post.caption)
                post_comments = (
                    session.query(models.PlatformComment)
                    .filter(models.PlatformComment.platform_post_id == post.id)
                    .order_by(models.PlatformComment.published_at.desc().nullslast())
                    .limit(200)
                    .all()
                )
                comments.extend(comment.text for comment in post_comments if comment.text)

    for mention in mentions:
        if not isinstance(mention, dict):
            continue
        if mention.get("followers"):
            try:
                followers = max(followers, int(mention["followers"]))
            except (TypeError, ValueError):
                pass
        if mention.get("professional_titles"):
            titles.extend(str(item) for item in mention["professional_titles"])
        if mention.get("credentials"):
            credentials.extend(str(item) for item in mention["credentials"])

    content = "\n\n".join(
        filter(None, [piece for row in sources for piece in (row.get("title"), row.get("content"))])
    )[:4000]
    context = "\n\n".join(filter(None, [m.get("context") for m in mentions if isinstance(m, dict)]))[:4000]
    if bio_parts:
        content = "\n\n".join([content, *bio_parts[:12]])[:8000]

    candidate = {
        "influencer_id": str(influencer.id),
        "canonical_name": influencer.canonical_name,
        "platforms": platforms,
        "profile_urls": profile_urls,
        "credentials": credentials,
        "professional_titles": titles,
        "mentions": mentions,
        "data_source_count": len(source_urls) + len(profiles if include_platform else []),
        "source_url": source_urls[0] if source_urls else (profile_urls[0] if profile_urls else ""),
        "source_urls": source_urls or profile_urls,
        "bio": "\n".join(bio_parts)[:4000],
        "content": content,
        "context": context,
        "comments": comments[:comment_limit],
        "followers": followers,
        "average_engagement": average_engagement or int(engagement_rate * 100) if engagement_rate else 0,
        "engagement_rate": engagement_rate,
        "verified": verified,
        "primary_location": influencer.primary_location,
        "embedding": influencer.embedding if isinstance(influencer.embedding, dict) else {},
    }
    return candidate


def persist_candidate_snapshot(
    session: Session,
    campaign_id: UUID,
    influencer_id: UUID,
    candidate: dict[str, Any],
) -> models.CandidateSnapshot:
    snapshot = models.CandidateSnapshot(
        id=uuid4(),
        campaign_id=campaign_id,
        influencer_id=influencer_id,
        snapshot=candidate,
        platform_fetch_watermark=datetime.now(UTC),
        built_at=datetime.now(UTC),
    )
    session.add(snapshot)
    return snapshot


def _sources_summary(session: Session, influencer_uuid: UUID, campaign_uuid: UUID) -> list[dict]:
    rows = (
        session.query(models.CrawlSourceInfluencer, models.CrawlSource)
        .join(models.CrawlSource, models.CrawlSource.id == models.CrawlSourceInfluencer.crawl_source_id)
        .filter(
            models.CrawlSourceInfluencer.influencer_id == influencer_uuid,
            models.CrawlSource.campaign_id == campaign_uuid,
        )
        .all()
    )
    if rows:
        return [
            {
                "url": source.url,
                "title": source.title,
                "status": source.status,
                "relevance_score": source.relevance_score,
                "content": source.content,
                "mention_id": link.mention_id,
                "mention": link.mention,
            }
            for link, source in rows
        ]

    legacy_rows = (
        session.query(models.CrawlSource)
        .filter(
            models.CrawlSource.influencer_id == influencer_uuid,
            models.CrawlSource.campaign_id == campaign_uuid,
        )
        .all()
    )
    return [
        {
            "url": row.url,
            "title": row.title,
            "status": row.status,
            "relevance_score": row.relevance_score,
            "content": row.content,
        }
        for row in legacy_rows
    ]
