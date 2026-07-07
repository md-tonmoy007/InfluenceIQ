"""Platform enrichment Celery task."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.exc import OperationalError

from backend.core.celery.app import celery_app
from backend.core.database import models
from backend.pipeline.content.enrichment import (
    collect_platform_urls_for_influencer,
    compute_and_persist_embedding,
    fetch_profiles_for_urls,
    persist_enrichment,
)
from backend.pipeline.tasks._common import (
    db_session,
    publish_event,
    refresh_campaign_status,
    set_phase,
)

log = logging.getLogger(__name__)


@celery_app.task(name="backend.pipeline.tasks.enrich.enrich_influencer_platforms", bind=True, max_retries=2)
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

    from backend.pipeline.tasks.score import score_influencer

    score_influencer.delay(campaign_id, influencer_id)
    set_phase(campaign_id, phase="scoring")
    return {"campaign_id": campaign_id, "influencer_id": influencer_id, **result}


__all__ = ["enrich_influencer_platforms_task"]
