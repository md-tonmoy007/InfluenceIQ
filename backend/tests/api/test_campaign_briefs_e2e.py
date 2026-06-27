"""End-to-end contract tests for campaign briefs (drafts, contracts, aggregates)."""

from __future__ import annotations

import os
import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routers import campaigns as campaigns_router
from backend.core.auth import get_current_user
from backend.core.database import models
from backend.core.database.session import get_db


def _fake_user() -> models.User:
    return models.User(
        id=uuid.uuid4(),
        email="briefs@example.com",
        password_hash="x",
        name="Brief User",
        company_name="Acme",
    )


class BriefSnapshotGoalsTest(unittest.TestCase):
    def test_brief_snapshot_accepts_goals_array(self) -> None:
        from backend.api.schemas.campaign import BriefSnapshot

        snapshot = BriefSnapshot(
            brand_name="Northwind",
            goals=["Product Launch", "Brand Awareness"],
            goal="Product Launch, Brand Awareness",
        )
        dumped = snapshot.model_dump(exclude_none=True)
        self.assertEqual(dumped["goals"], ["Product Launch", "Brand Awareness"])

    def test_campaign_create_supports_start_pipeline_false(self) -> None:
        from backend.api.schemas.campaign import CampaignCreate

        payload = CampaignCreate(
            product="Trail pack",
            industry="outdoor",
            start_pipeline=False,
        )
        self.assertFalse(payload.start_pipeline)


class CampaignResponseBriefFieldsTest(unittest.TestCase):
    def test_response_includes_shortlist_and_contract_counts(self) -> None:
        from backend.api.schemas.campaign import CampaignResponse

        props = CampaignResponse.model_json_schema().get("properties", {})
        self.assertIn("shortlisted_count", props)
        self.assertIn("contracted_count", props)


class CampaignBriefRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(campaigns_router.router)
        self.client = TestClient(self.app)
        self.app.dependency_overrides.clear()
        self.user = _fake_user()
        self.other_user = _fake_user()
        self.campaign = models.Campaign(
            id=uuid.uuid4(),
            product="Trail pack",
            niche="outdoor",
            goals="launch",
            status="draft",
            created_by=self.user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            brief_snapshot={"brand_name": "Northwind", "goals": ["Product Launch"]},
        )

        class _Query:
            def __init__(self, outer: "CampaignBriefRouterTest"):
                self.outer = outer

            def filter(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

            def offset(self, _n):
                return self

            def limit(self, _n):
                return self

            def join(self, *args, **kwargs):
                return self

            def first(self):
                return self.outer.campaign

            def all(self):
                if self.outer.campaign.created_by == self.outer.user.id:
                    return [self.outer.campaign]
                return []

            def count(self):
                return len(self.all())

            def scalar(self):
                return None

        class _Session:
            def __init__(self, outer: "CampaignBriefRouterTest"):
                self.outer = outer
                self.added: list[object] = []

            def query(self, *entities):
                return _Query(self.outer)

            def add(self, obj):
                self.added.append(obj)
                if isinstance(obj, models.Campaign):
                    now = datetime.now(UTC)
                    if getattr(obj, "created_at", None) is None:
                        obj.created_at = now
                    if getattr(obj, "updated_at", None) is None:
                        obj.updated_at = now
                    self.outer.campaign = obj

            def commit(self):
                return None

            def refresh(self, obj):
                if getattr(obj, "id", None) is None:
                    obj.id = uuid.uuid4()
                now = datetime.now(UTC)
                if getattr(obj, "created_at", None) is None:
                    obj.created_at = now
                if getattr(obj, "updated_at", None) is None:
                    obj.updated_at = now

            def delete(self, obj):
                return None

            def close(self):
                return None

        self.session = _Session(self)

        def _override_get_db():
            yield self.session

        self.app.dependency_overrides[get_db] = _override_get_db
        self.app.dependency_overrides[get_current_user] = lambda: self.user

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_create_draft_does_not_start_pipeline(self) -> None:
        with (
            patch.object(campaigns_router, "initialize_pipeline_state") as init_state,
            patch("backend.pipeline.tasks.start_campaign") as start_campaign,
            patch.object(campaigns_router, "get_current_user_optional", return_value=self.user),
        ):
            response = self.client.post(
                "/api/campaigns",
                json={
                    "product": "Draft product",
                    "industry": "beauty",
                    "start_pipeline": False,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "draft")
        init_state.assert_not_called()
        start_campaign.assert_not_called()

    def test_patch_draft_updates_brief_snapshot_goals(self) -> None:
        response = self.client.patch(
            f"/api/campaigns/{self.campaign.id}",
            json={
                "brief_snapshot": {
                    "brand_name": "Northwind",
                    "goals": ["Sales Conversion"],
                    "goal": "Sales Conversion",
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["brief_snapshot"]["goals"], ["Sales Conversion"])

    def test_submit_draft_starts_pipeline(self) -> None:
        with (
            patch.object(campaigns_router, "initialize_pipeline_state"),
            patch.object(campaigns_router, "get_pipeline_state", return_value={"phase": "initializing"}),
            patch("backend.pipeline.tasks.start_campaign", return_value={"started": True}),
        ):
            response = self.client.post(f"/api/campaigns/{self.campaign.id}/submit")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "running")

    def test_duplicate_creates_new_draft(self) -> None:
        source_id = self.campaign.id
        response = self.client.post(f"/api/campaigns/{source_id}/duplicate")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "draft")
        self.assertNotEqual(body["id"], str(source_id))

    def test_list_campaigns_requires_auth(self) -> None:
        self.app.dependency_overrides.pop(get_current_user, None)
        response = self.client.get("/api/campaigns")
        self.assertEqual(response.status_code, 401)

    def test_cross_user_get_returns_404(self) -> None:
        self.campaign.created_by = self.other_user.id
        response = self.client.get(f"/api/campaigns/{self.campaign.id}")
        self.assertEqual(response.status_code, 404)
