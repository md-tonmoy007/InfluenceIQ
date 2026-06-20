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
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.cache.event_log import emit_event
from backend.core.cache.pipeline_state import update_pipeline_state
from backend.core.database import models
from backend.core.database.session import SessionLocal

log = logging.getLogger(__name__)


@contextmanager
def db_session() -> Iterator[Session]:
    """Yield a request-scoped DB session and close it deterministically.

    Celery tasks run in their own worker process; we never share the
    FastAPI ``Depends(get_db)`` session across the queue boundary.
    The session is closed even on exception, and the rollback is
    best-effort — connection-level failures bubble up so the worker
    can apply its retry policy.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


def get_campaign(session: Session, campaign_id: str) -> models.Campaign:
    """Load a campaign by stringified UUID, raising ValueError if absent.

    The task chain always passes ``campaign_id`` as a string (Celery
    JSON serialises UUIDs poorly in older versions), so we accept the
    string here and let the DB do the type validation via the UUID
    column.
    """
    try:
        campaign_uuid = UUID(campaign_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"campaign_id is not a valid UUID: {campaign_id!r}") from exc
    campaign = session.get(models.Campaign, campaign_uuid)
    if campaign is None:
        raise ValueError(f"Campaign {campaign_id} does not exist")
    return campaign


def publish_event(campaign_id: str, event_type: str, **payload: Any) -> dict:
    """Wrap :func:`backend.core.cache.event_log.emit_event` for the task bodies.

    Every public Celery task calls this exactly once per phase boundary
    so the WebSocket stream and the persistent replay log stay in sync.
    Unknown event types are accepted verbatim — the WebSocket client
    filters by type, the API does not need a registry.
    """
    try:
        return emit_event(campaign_id, event_type, payload)
    except Exception as exc:  # pragma: no cover - Redis is best-effort
        # The event log is observability, not a source of truth. A
        # transient Redis outage must not fail the pipeline.
        log.warning("Failed to publish event %s for campaign %s: %s",
                    event_type, campaign_id, exc)
        return {}


def set_phase(campaign_id: str, **fields: Any) -> None:
    """Update the pipeline-state hash. Same best-effort guarantee as :func:`publish_event`."""
    try:
        update_pipeline_state(campaign_id, **fields)
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to update pipeline state for %s: %s", campaign_id, exc)


def campaign_query_payload(campaign: models.Campaign) -> dict:
    """Project the campaign ORM row into the query-generation input shape.

    The query generator consumes ``product``, ``niche``, ``goals``,
    ``target_audience`` and ``preferred_platforms``. All of those are
    columns on the ``Campaign`` model; we copy them into a plain dict
    so the task body stays decoupled from SQLAlchemy state.
    """
    return {
        "campaign_id": str(campaign.id),
        "product": campaign.product,
        "niche": campaign.niche,
        "goals": campaign.goals,
        "target_audience": campaign.target_audience,
        "preferred_platforms": list(campaign.preferred_platforms or []),
    }


__all__ = [
    "campaign_query_payload",
    "db_session",
    "get_campaign",
    "publish_event",
    "set_phase",
]
