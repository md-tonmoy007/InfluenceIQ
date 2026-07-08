"""Platform enrichment Celery task."""

from __future__ import annotations

import logging
from uuid import UUID

from celery.exceptions import Retry, SoftTimeLimitExceeded
from sqlalchemy.exc import OperationalError

from backend.core.celery.app import celery_app
from backend.core.config import settings
from backend.core.database import models
from backend.pipeline.content.enrichment import (
    collect_platform_urls_for_influencer,
    compute_and_persist_embedding,
    fetch_profiles_for_urls,
    persist_enrichment,
    persist_post_comments,
)
from backend.pipeline.content.providers.comments.base import fetch_post_comments
from backend.pipeline.tasks._common import (
    db_session,
    publish_event,
    refresh_campaign_status,
    set_phase,
)

log = logging.getLogger(__name__)


def _enqueue_scoring(campaign_id: str, influencer_id: str) -> None:
    """Hand this influencer off to scoring.

    Enrichment is the *only* trigger for scoring, and scoring degrades
    gracefully when platform data is missing (it falls back to mention/crawl
    signals). So scoring must be dispatched on every terminal enrichment path —
    success, provider failure, timeout, or hard error — otherwise a single
    failed enrichment strands one influencer and freezes the whole campaign.
    """
    from backend.pipeline.tasks.score import score_influencer

    score_influencer.delay(campaign_id, influencer_id)
    set_phase(campaign_id, phase="scoring")


@celery_app.task(
    name="backend.pipeline.tasks.enrich.enrich_influencer_platforms",
    bind=True,
    max_retries=2,
    # Backstop: a slow/unresponsive platform provider must never pin a worker
    # slot indefinitely (that stalls the whole scraping queue and freezes the
    # campaign). The soft limit raises SoftTimeLimitExceeded INSIDE the task so
    # we can catch it, still enqueue scoring, and return normally — which acks
    # the message under task_acks_late and avoids a poison-redelivery loop that
    # a hard time_limit kill would cause.
    soft_time_limit=300,
)
def enrich_influencer_platforms_task(self, campaign_id: str, influencer_id: str) -> dict:
    """Fetch structured platform data for one influencer, then score."""
    log.info("enrich_influencer_platforms campaign_id=%s influencer_id=%s", campaign_id, influencer_id)
    try:
        campaign_uuid = UUID(campaign_id)
        influencer_uuid = UUID(influencer_id)
    except (TypeError, ValueError):
        return {"status": "invalid_id", "influencer_id": influencer_id}

    # Step 1: brief DB read — collect platform URLs, then close the session.
    with db_session() as session:
        campaign = session.get(models.Campaign, campaign_uuid)
        if campaign is None:
            return {"status": "missing_campaign", "influencer_id": influencer_id}
        if campaign.status in {"cancelled", "failed"}:
            return {"status": "campaign_stopped", "influencer_id": influencer_id}

        crawl_sources = (
            session.query(models.CrawlSource)
            .join(models.CrawlSourceInfluencer)
            .filter(
                models.CrawlSource.campaign_id == campaign_uuid,
                models.CrawlSourceInfluencer.influencer_id == influencer_uuid,
            )
            .all()
        )
        urls = collect_platform_urls_for_influencer(session, influencer_uuid, crawl_sources)

    try:
        # Step 2: HTTP fetches — no DB session open, so no transaction is held.
        fetched = fetch_profiles_for_urls(urls)

        # Step 3: persist results — brief DB write session.
        try:
            with db_session() as session:
                result = persist_enrichment(session, influencer_uuid, fetched)
                if result.get("profiles", 0) > 0:
                    compute_and_persist_embedding(session, influencer_uuid)
                refresh_campaign_status(session, campaign_id)
        except OperationalError as exc:
            if "deadlock detected" not in str(exc).lower():
                raise
            log.warning("enrich_influencer_platforms: deadlock persisting influencer=%s, retrying", influencer_id)
            raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 10))
    except SoftTimeLimitExceeded:
        # Provider fetch/persist overran the budget. Free the worker and let
        # scoring proceed with whatever data already exists rather than
        # stranding this influencer (which would freeze the campaign).
        log.warning(
            "enrich_influencer_platforms: soft time limit hit campaign=%s influencer=%s — scoring with existing data",
            campaign_id,
            influencer_id,
        )
        _enqueue_scoring(campaign_id, influencer_id)
        return {"status": "enrich_timeout", "campaign_id": campaign_id, "influencer_id": influencer_id}
    except Retry:
        # Deliberate deadlock retry (self.retry above) — let Celery reschedule.
        raise
    except Exception as exc:
        # Enrichment failed hard (DB error, provider blow-up, retries exhausted).
        # Do NOT strand scoring: it degrades gracefully without platform data, so
        # dispatch it anyway so the campaign can still reach completion.
        log.exception(
            "enrich_influencer_platforms: enrichment failed campaign=%s influencer=%s: %s — scoring anyway",
            campaign_id,
            influencer_id,
            exc,
        )
        _enqueue_scoring(campaign_id, influencer_id)
        return {"status": "enrich_error", "campaign_id": campaign_id, "influencer_id": influencer_id}

    from backend.core.cache.pipeline_state import increment_pipeline_counter

    increment_pipeline_counter(campaign_id, "platforms_enriched")
    if result.get("failed"):
        increment_pipeline_counter(campaign_id, "enrichment_failed", int(result["failed"]))

    publish_event(
        campaign_id,
        "platform.enriched",
        influencer_id=influencer_id,
        profiles=result.get("profiles", 0),
        failed=result.get("failed", 0),
        coverage=result.get("coverage", {}),
    )

    # Step 4: optionally fetch real audience comments for recent posts.
    if settings.COMMENT_FETCH_ON_ENRICH and result.get("profiles", 0) > 0:
        try:
            _fetch_and_persist_comments(campaign_id, influencer_uuid)
        except Exception as exc:
            log.warning(
                "enrich_influencer_platforms: comment fetch failed campaign=%s influencer=%s: %s",
                campaign_id,
                influencer_id,
                exc,
            )

    _enqueue_scoring(campaign_id, influencer_id)
    return {"campaign_id": campaign_id, "influencer_id": influencer_id, **result}


def _fetch_and_persist_comments(campaign_id: str, influencer_uuid: UUID) -> None:
    """Fetch real audience comments for the most-recent posts and persist them.

    Runs outside the main enrichment transaction so HTTP latency does not
    hold a DB connection. Failures are logged and swallowed.
    """
    from backend.core.database import models

    targets: list[tuple[str, UUID, str, int]] = []  # (platform, post_id, external_id, limit)
    with db_session() as session:
        profiles = (
            session.query(models.PlatformProfile)
            .filter(models.PlatformProfile.influencer_id == influencer_uuid)
            .all()
        )
        for profile in profiles:
            if profile.platform not in {"youtube", "instagram", "tiktok"}:
                continue
            posts = (
                session.query(models.PlatformPost)
                .filter(models.PlatformPost.platform_profile_id == profile.id)
                .order_by(models.PlatformPost.published_at.desc().nullslast())
                .limit(settings.ENRICH_COMMENT_POST_LIMIT)
                .all()
            )
            for post in posts:
                external_id = str(post.platform_post_id or "")
                post_url = str(post.post_url or "")
                if not external_id and not post_url:
                    continue
                if profile.platform == "youtube":
                    limit = settings.YOUTUBE_COMMENTS_PER_POST
                else:
                    limit = settings.ENRICH_COMMENTS_PER_POST
                targets.append((profile.platform, post.id, external_id or post_url, limit))

    if not targets:
        return

    import time

    fetched: list[tuple[UUID, list]] = []
    deadline = time.monotonic() + settings.ENRICH_COMMENT_FETCH_BUDGET_SEC
    for platform, post_id, external_id_or_url, limit in targets:
        if time.monotonic() >= deadline:
            log.warning(
                "comment fetch budget exhausted influencer=%s — %d posts unfetched",
                influencer_uuid,
                len(targets) - len(fetched),
            )
            break
        try:
            comments = fetch_post_comments(
                platform,
                post_url=external_id_or_url if "://" in external_id_or_url else "",
                post_external_id=external_id_or_url if "://" not in external_id_or_url else "",
                limit=limit,
            )
        except Exception as exc:
            log.warning(
                "comment fetch skipped post=%s platform=%s: %s",
                post_id,
                platform,
                exc,
            )
            continue
        if comments:
            fetched.append((post_id, comments))

    if not fetched:
        return

    with db_session() as session:
        for post_id, comments in fetched:
            post = session.get(models.PlatformPost, post_id)
            if post is None:
                continue
            try:
                persist_post_comments(session, post, comments)
            except Exception as exc:
                log.warning("persist_post_comments failed post=%s: %s", post_id, exc)


__all__ = ["enrich_influencer_platforms_task"]
