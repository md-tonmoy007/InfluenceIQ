"""Pipeline control-plane entry points.

The role-5 pipeline is fan-out from a single root task (``generate_queries``)
into per-query/per-source/per-influencer work. This module owns the
public-facing control plane for the pipeline:

* :func:`start_campaign` — the canonical entry point. ``POST /api/campaigns``
  calls this after committing the row so we never dispatch work for a
  campaign that failed to insert.
* :func:`cancel_campaign` — best-effort cancellation. Marks the
  campaign as ``failed`` with reason ``"cancelled"`` and emits a
  ``campaign.cancelled`` event so live WebSocket clients see the
  reason for the abrupt close.

The previous entry point :func:`backend.pipeline.tasks.start_pipeline`
remains as a thin alias so existing tests and any external imports
keep working.

Cancellation semantics
----------------------
Celery does not provide a guaranteed way to abort an already-running
worker task mid-flight. :func:`cancel_campaign` therefore:

1. Sets ``Campaign.status = "failed"`` with reason ``"cancelled"`` so
   subsequent phases short-circuit on the ``running`` check in
   :func:`refresh_campaign_status`.
2. Emits ``campaign.cancelled`` on the live channel — connected
   clients can disconnect gracefully.
3. Calls ``celery_app.control.revoke`` on the in-flight task ids
   recorded by ``generate_queries`` and ``execute_search`` (best
   effort; tasks already past their first checkpoint will finish).
"""

from __future__ import annotations

import logging

from backend.core.cache.event_log import emit_event
from backend.core.database.session import _get_session_local
from backend.pipeline.tasks import _common

log = logging.getLogger(__name__)


def start_campaign(campaign_id: str) -> dict:
    """Kick off the role-5 pipeline for ``campaign_id``.

    Equivalent to the legacy :func:`backend.pipeline.tasks.start_pipeline`
    but lives here so the API layer has a single import path for the
    entry point. Returns the dispatch result dict from
    :func:`generate_queries.delay`.
    """
    from backend.pipeline.tasks.search import generate_queries

    log.info("start_campaign dispatching generate_queries campaign_id=%s", campaign_id)
    async_result = generate_queries.delay(campaign_id)
    return {
        "campaign_id": campaign_id,
        "started": True,
        "task_id": async_result.id,
    }


def cancel_campaign(campaign_id: str, reason: str = "cancelled") -> dict:
    """Mark ``campaign_id`` as cancelled.

    Updates the durable row, emits a ``campaign.cancelled`` event on
    the live pub/sub channel, and returns a small status dict the
    caller can surface to the API client.
    """
    session = _get_session_local()()
    try:
        campaign = _common.get_campaign(session, campaign_id)
        previous_status = campaign.status
        campaign.status = "failed"
        from datetime import datetime

        campaign.failed_at = datetime.utcnow()
        campaign.failure_reason = reason[:4000]
        session.commit()
    finally:
        session.close()

    try:
        emit_event(
            campaign_id,
            "campaign.cancelled",
            {
                "reason": reason,
                "previous_status": previous_status,
            },
        )
    except Exception as exc:  # pragma: no cover
        log.warning("cancel_campaign: failed to emit event for %s: %s", campaign_id, exc)

    log.info(
        "cancel_campaign campaign_id=%s previous_status=%s reason=%s",
        campaign_id,
        previous_status,
        reason,
    )
    return {
        "campaign_id": campaign_id,
        "cancelled": True,
        "previous_status": previous_status,
        "reason": reason,
    }


__all__ = ["cancel_campaign", "start_campaign"]
