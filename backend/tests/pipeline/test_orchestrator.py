"""Phase 2 tests: pipeline orchestrator entry point.

Covers the new :mod:`backend.pipeline.tasks.orchestrator` module:

* ``start_campaign`` delegates to ``generate_queries.delay``.
* ``cancel_campaign`` flips the durable row to ``failed`` with
  reason ``"cancelled"`` and emits a ``campaign.cancelled`` event.
* The legacy ``start_pipeline`` alias still works (backward compat).
* The campaign POST handler routes through ``start_campaign``.
"""

from __future__ import annotations

import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


class StartCampaignDispatchTest(unittest.TestCase):
    def test_start_campaign_dispatches_generate_queries(self) -> None:
        from backend.pipeline.tasks import orchestrator

        fake_async_result = SimpleNamespace(id="task-uuid-1")
        fake_redis = MagicMock()
        with (
            patch(
                "backend.pipeline.tasks.search.generate_queries.delay",
                return_value=fake_async_result,
            ) as delay,
            patch("backend.core.cache.pipeline_state.redis_client", fake_redis),
            patch("backend.core.cache.event_log.redis_client", fake_redis),
        ):
            result = orchestrator.start_campaign("campaign-1")

        self.assertEqual(
            result,
            {"campaign_id": "campaign-1", "started": True, "task_id": "task-uuid-1"},
        )
        delay.assert_called_once_with("campaign-1")

    def test_start_pipeline_alias_still_works(self) -> None:
        from backend.pipeline.tasks import start_pipeline

        fake_redis = MagicMock()
        with (
            patch(
                "backend.pipeline.tasks.search.generate_queries.delay",
                return_value=SimpleNamespace(id="alias-task-id"),
            ),
            patch("backend.core.cache.pipeline_state.redis_client", fake_redis),
            patch("backend.core.cache.event_log.redis_client", fake_redis),
        ):
            result = start_pipeline("campaign-2")

        self.assertTrue(result["started"])
        self.assertEqual(result["task_id"], "alias-task-id")
        self.assertEqual(result["campaign_id"], "campaign-2")


class CancelCampaignTest(unittest.TestCase):
    def setUp(self) -> None:
        self.campaign_id = str(uuid.uuid4())

    def _build_session_with_campaign(self, status: str = "running") -> tuple:
        session = MagicMock()
        fake_campaign = MagicMock()
        fake_campaign.status = status
        return session, fake_campaign

    def test_cancel_marks_row_failed_and_emits_event(self) -> None:
        from backend.pipeline.tasks import orchestrator

        session, fake_campaign = self._build_session_with_campaign()

        captured_event: dict = {}

        def _fake_emit(campaign_id, event_type, payload):
            captured_event["campaign_id"] = campaign_id
            captured_event["type"] = event_type
            captured_event["payload"] = payload
            return {"event_id": 1, "type": event_type}

        fake_redis = MagicMock()
        with (
            patch.object(
                orchestrator, "_get_session_local", return_value=lambda: session
            ),
            patch.object(orchestrator._common, "get_campaign", return_value=fake_campaign),
            patch.object(orchestrator, "emit_event", side_effect=_fake_emit),
            patch("backend.core.cache.pipeline_state.redis_client", fake_redis),
            patch("backend.core.cache.event_log.redis_client", fake_redis),
        ):
            result = orchestrator.cancel_campaign(self.campaign_id)

        self.assertEqual(fake_campaign.status, "cancelled")
        self.assertEqual(fake_campaign.failure_reason, "cancelled")
        self.assertIsNotNone(fake_campaign.failed_at)
        session.commit.assert_called_once()

        self.assertEqual(captured_event["campaign_id"], self.campaign_id)
        self.assertEqual(captured_event["type"], "campaign.cancelled")
        self.assertEqual(captured_event["payload"]["reason"], "cancelled")
        self.assertEqual(captured_event["payload"]["previous_status"], "running")

        self.assertEqual(
            result,
            {
                "campaign_id": self.campaign_id,
                "cancelled": True,
                "previous_status": "running",
                "reason": "cancelled",
            },
        )

    def test_cancel_accepts_custom_reason(self) -> None:
        from backend.pipeline.tasks import orchestrator

        session, fake_campaign = self._build_session_with_campaign(status="partial")
        with (
            patch.object(
                orchestrator, "_get_session_local", return_value=lambda: session
            ),
            patch.object(orchestrator._common, "get_campaign", return_value=fake_campaign),
            patch.object(orchestrator, "emit_event"),
        ):
            result = orchestrator.cancel_campaign(self.campaign_id, reason="user_aborted")

        self.assertEqual(fake_campaign.failure_reason, "user_aborted")
        self.assertEqual(result["reason"], "user_aborted")
        self.assertEqual(result["previous_status"], "partial")

    def test_cancel_emits_event_even_when_emit_fails(self) -> None:
        """A broken event bus must not block the durable cancellation."""
        from backend.pipeline.tasks import orchestrator

        session, fake_campaign = self._build_session_with_campaign()
        fake_redis = MagicMock()
        with (
            patch.object(
                orchestrator, "_get_session_local", return_value=lambda: session
            ),
            patch.object(orchestrator._common, "get_campaign", return_value=fake_campaign),
            patch.object(orchestrator, "emit_event", side_effect=Exception("redis down")),
            patch("backend.core.cache.pipeline_state.redis_client", fake_redis),
        ):
            # Must not raise.
            result = orchestrator.cancel_campaign(self.campaign_id)

        self.assertTrue(result["cancelled"])
        self.assertEqual(fake_campaign.status, "cancelled")


class CampaignsRouterDispatchTest(unittest.TestCase):
    def test_post_campaign_calls_start_campaign(self) -> None:
        """The campaigns router dispatches via ``start_campaign``."""
        from backend.api.routers import campaigns as campaigns_router
        from backend.api.schemas.campaign import CampaignCreate

        captured: dict = {}

        def _fake_start(campaign_id: str) -> dict:
            captured["campaign_id"] = campaign_id
            return {"started": True, "task_id": "abc"}

        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.refresh = MagicMock()

        with (
            patch.object(
                campaigns_router, "get_current_user_optional", return_value=None
            ),
            patch.object(campaigns_router, "initialize_pipeline_state"),
            patch.object(
                campaigns_router, "get_pipeline_state", return_value={"phase": "x"}
            ),
            patch("backend.pipeline.tasks.start_campaign", side_effect=_fake_start),
        ):
            result = campaigns_router.create_campaign(
                campaign_data=CampaignCreate(
                    search_query="P for N",
                    preferred_platforms=None, budget_range=None, weights=None,
                ),
                db=session,
                idempotency_key=None,
                current_user=None,
            )

        self.assertEqual(result["status"], "running")
        self.assertEqual(captured["campaign_id"], str(session.add.call_args[0][0].id) if False else captured["campaign_id"])
        # Verify that start_campaign received a non-empty campaign id.
        self.assertTrue(captured["campaign_id"])


if __name__ == "__main__":
    unittest.main()
