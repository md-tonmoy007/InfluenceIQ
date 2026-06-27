"""Unit tests for campaign run reset helpers."""

from __future__ import annotations

import os
import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, call

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from backend.core.database import models
from backend.pipeline.campaign_reset import (
    clear_campaign_run_artifacts,
    reset_campaign_lifecycle,
)


class CampaignResetTest(unittest.TestCase):
    def test_clear_campaign_run_artifacts_deletes_all_run_tables(self) -> None:
        campaign_id = uuid.uuid4()
        db = MagicMock()
        query = MagicMock()
        db.query.return_value = query
        query.filter.return_value = query

        clear_campaign_run_artifacts(db, campaign_id)

        self.assertEqual(db.query.call_count, 7)
        delete_calls = [c for c in query.method_calls if c[0] == "delete"]
        self.assertEqual(len(delete_calls), 6)
        for delete_call in delete_calls:
            self.assertEqual(delete_call.kwargs.get("synchronize_session"), False)

    def test_reset_campaign_lifecycle_to_draft(self) -> None:
        campaign = models.Campaign(
            id=uuid.uuid4(),
            product="Test",
            niche="tech",
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            failed_at=None,
            failure_reason=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        reset_campaign_lifecycle(campaign, to_draft=True)

        self.assertEqual(campaign.status, "draft")
        self.assertIsNone(campaign.started_at)
        self.assertIsNone(campaign.completed_at)
        self.assertIsNone(campaign.failed_at)
        self.assertIsNone(campaign.failure_reason)

    def test_reset_campaign_lifecycle_to_running(self) -> None:
        campaign = models.Campaign(
            id=uuid.uuid4(),
            product="Test",
            niche="tech",
            status="failed",
            started_at=datetime.now(UTC),
            completed_at=None,
            failed_at=datetime.now(UTC),
            failure_reason="boom",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        reset_campaign_lifecycle(campaign, to_draft=False)

        self.assertEqual(campaign.status, "running")
        self.assertIsNotNone(campaign.started_at)
        self.assertIsNone(campaign.completed_at)
        self.assertIsNone(campaign.failed_at)
        self.assertIsNone(campaign.failure_reason)


if __name__ == "__main__":
    unittest.main()
