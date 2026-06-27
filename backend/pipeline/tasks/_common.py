"""Shared helpers used by every Celery task body.

This module intentionally sits at ``backend.pipeline.tasks._common`` (private) so
``from backend.pipeline.tasks import ...`` only re-exports the public task functions
and the chain builder. Anything cross-cutting — Redis events, pipeline
state updates, DB session lifecycle, error wrapping — lives here.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.cache.event_log import emit_event
from backend.core.cache.pipeline_state import get_pipeline_state, update_pipeline_state
from backend.core.database import models
from backend.core.database.session import _get_session_local

log = logging.getLogger(__name__)


@contextmanager
def db_session() -> Iterator[Session]:
    """Yield a request-scoped DB session and close it deterministically."""
    session = _get_session_local()()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


# Backwards-compat shim: some callers (and the existing test suite)
# patch ``backend.pipeline.tasks._common.SessionLocal`` to inject a
# fake session. Re-bind the legacy name so those patches keep working
# even though the canonical entry point is now
# :func:`_get_session_local`.
SessionLocal = _get_session_local


def get_campaign(session: Session, campaign_id: str) -> models.Campaign:
    """Load a campaign by stringified UUID, raising ValueError if absent."""
    try:
        campaign_uuid = UUID(campaign_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"campaign_id is not a valid UUID: {campaign_id!r}") from exc
    campaign = session.get(models.Campaign, campaign_uuid)
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} does not exist")
    return campaign


def publish_event(campaign_id: str, event_type: str, **payload: Any) -> dict:
    """Wrap event emission for task bodies."""
    try:
        return emit_event(campaign_id, event_type, payload)
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to publish event %s for campaign %s: %s", event_type, campaign_id, exc)
        return {}


def emit_campaign_lifecycle_event(
    campaign_id: str,
    event_type: str,
    *,
    status: str | None = None,
    reason: str | None = None,
) -> None:
    """Emit a terminal or lifecycle campaign event and sync Redis status."""
    payload: dict[str, Any] = {}
    if status:
        payload["status"] = status
    if reason:
        payload["reason"] = reason
    state = get_pipeline_state(campaign_id) or {}
    payload.update(
        {
            "scores_computed": int(state.get("scores_computed") or 0),
            "influencers_found": int(state.get("influencers_found") or 0),
            "urls_scraped": int(state.get("urls_scraped") or 0),
        }
    )
    publish_event(campaign_id, event_type, **payload)
    if status:
        set_phase(campaign_id, status=status)


def set_phase(campaign_id: str, **fields: Any) -> None:
    """Update the pipeline-state hash."""
    try:
        update_pipeline_state(campaign_id, **fields)
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to update pipeline state for %s: %s", campaign_id, exc)


def mark_campaign_running(session: Session, campaign_id: str) -> None:
    campaign = get_campaign(session, campaign_id)
    campaign.status = "running"
    campaign.started_at = campaign.started_at or datetime.utcnow()
    campaign.failed_at = None
    campaign.failure_reason = None


def mark_campaign_failed(session: Session, campaign_id: str, reason: str) -> None:
    campaign = get_campaign(session, campaign_id)
    campaign.status = "failed"
    campaign.failed_at = datetime.utcnow()
    campaign.failure_reason = reason[:4000]
    campaign.completed_at = None
    emit_campaign_lifecycle_event(
        campaign_id,
        "campaign.failed",
        status="failed",
        reason=reason[:4000],
    )


def refresh_campaign_status(session: Session, campaign_id: str) -> None:
    """Derive a durable campaign lifecycle status from current DB state."""
    try:
        campaign = get_campaign(session, campaign_id)

        total_sources = (
            session.query(models.CrawlSource)
            .filter(models.CrawlSource.campaign_id == campaign.id)
            .count()
        )
        pending_sources = (
            session.query(models.CrawlSource)
            .filter(
                models.CrawlSource.campaign_id == campaign.id,
                models.CrawlSource.status.in_(["pending", "scraped"]),
            )
            .count()
        )
        failed_sources = (
            session.query(models.CrawlSource)
            .filter(
                models.CrawlSource.campaign_id == campaign.id,
                models.CrawlSource.status == "failed",
            )
            .count()
        )

        linked_influencer_ids = {
            row[0]
            for row in session.query(models.CrawlSourceInfluencer.influencer_id)
            .join(models.CrawlSource, models.CrawlSource.id == models.CrawlSourceInfluencer.crawl_source_id)
            .filter(models.CrawlSource.campaign_id == campaign.id)
            .distinct()
            .all()
        }
        if not linked_influencer_ids:
            linked_influencer_ids = {
                row[0]
                for row in session.query(models.CrawlSource.influencer_id)
                .filter(
                    models.CrawlSource.campaign_id == campaign.id,
                    models.CrawlSource.influencer_id.isnot(None),
                )
                .distinct()
                .all()
            }

        scored_count = (
            session.query(models.InfluencerScore.influencer_id)
            .filter(models.InfluencerScore.campaign_id == campaign.id)
            .distinct()
            .count()
        )

        influencer_count = len(linked_influencer_ids)
        if total_sources == 0 or pending_sources > 0:
            campaign.status = "running"
            return

        if influencer_count == 0:
            campaign.status = "running"
            return

        if scored_count < influencer_count:
            campaign.status = "running"
            return

        if failed_sources == total_sources and total_sources > 0 and scored_count == 0:
            campaign.status = "failed"
            campaign.failed_at = campaign.failed_at or datetime.utcnow()
            campaign.completed_at = None
            emit_campaign_lifecycle_event(
                campaign_id,
                "campaign.failed",
                status="failed",
                reason=campaign.failure_reason or "All sources failed",
            )
            return

        if failed_sources > 0:
            campaign.status = "partial"
        else:
            campaign.status = "completed"
        campaign.completed_at = campaign.completed_at or datetime.utcnow()
        campaign.failed_at = None if campaign.status == "completed" else campaign.failed_at

        if campaign.status == "completed":
            emit_campaign_lifecycle_event(
                campaign_id,
                "campaign.completed",
                status="completed",
            )
        elif campaign.status == "partial":
            emit_campaign_lifecycle_event(
                campaign_id,
                "campaign.partial",
                status="partial",
            )
    except AttributeError:
        return


def campaign_query_payload(campaign: models.Campaign) -> dict:
    """Project the campaign ORM row into the query-generation input shape."""
    return {
        "campaign_id": str(campaign.id),
        "product": campaign.product,
        "niche": campaign.niche,
        "goals": campaign.goals,
        "target_audience": campaign.target_audience,
        "preferred_platforms": list(campaign.preferred_platforms or []),
        "locations": list((campaign.brief_snapshot or {}).get("locations") or []),
    }


__all__ = [
    "campaign_query_payload",
    "db_session",
    "emit_campaign_lifecycle_event",
    "get_campaign",
    "mark_campaign_failed",
    "mark_campaign_running",
    "publish_event",
    "refresh_campaign_status",
    "set_phase",
]
