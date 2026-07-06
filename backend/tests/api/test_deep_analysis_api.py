"""Integration tests for the deep analysis API endpoints.

Tests the request/response contracts for:
- ``GET /deep-analysis/latest?campaign_id=...``
- ``POST /deep-analysis`` (cache hit/miss, queuing)
- ``GET /deep-analysis/{run_id}`` (polling)
- ``GET /reports/{report_id}``

Uses the same FakeSession/FakeQuery pattern as test_backend_contracts.py
so no Postgres/Redis is required.
"""

from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.auth import get_current_user
from backend.core.database import models
from backend.core.database.session import get_db


class FakeDeepQuery:
    """Specialised fake query for deep analysis models.

    Allows tests to pre-seed results, and filter() applies basic
    attribute-based filtering for status, cache_expires_at, and
    FK relationships.
    """
    def __init__(self, model, preloaded: list = None):
        self._model = model
        self._preloaded = preloaded or []
        self._conditions: list = []

    def filter(self, *args, **kwargs):
        self._conditions.extend(args)
        return self

    def _apply_filters(self) -> list:
        results = list(self._preloaded)
        for cond in self._conditions:
            results = [r for r in results if self._eval_filter(r, cond)]
        return results

    def _eval_filter(self, row, cond) -> bool:
        """Evaluate a SQLAlchemy BinaryExpression against a row."""
        import operator
        from sqlalchemy.sql.elements import BinaryExpression

        if not isinstance(cond, BinaryExpression):
            return True
        left = cond.left
        right = cond.right.value if hasattr(cond.right, 'value') else cond.right

        col_name = None
        if hasattr(left, 'key'):
            col_name = left.key
        elif hasattr(left, 'name'):
            col_name = left.name

        if col_name is None:
            return True

        if not hasattr(row, col_name):
            return True

        row_val = getattr(row, col_name, None)

        try:
            op_module = getattr(cond.operator, '__name__', str(cond.operator))
            if hasattr(cond.operator, '__name__'):
                op_name = cond.operator.__name__
            else:
                return True

            mapper = {
                'eq': lambda a, b: a == b,
                'ne': lambda a, b: a != b,
                'gt': lambda a, b: a is not None and b is not None and a > b,
                'lt': lambda a, b: a is not None and b is not None and a < b,
                'ge': lambda a, b: a is not None and b is not None and a >= b,
                'le': lambda a, b: a is not None and b is not None and a <= b,
                'eq_': lambda a, b: str(a) == str(b),
            }
            if op_name in mapper:
                return mapper[op_name](row_val, right)
        except Exception:
            pass
        return True

    def first(self):
        filtered = self._apply_filters()
        return filtered[0] if filtered else None

    def all(self):
        return list(self._apply_filters())

    def limit(self, _n):
        return self

    def offset(self, _n):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._apply_filters())

    def distinct(self):
        return self


class FakeDBSession:
    def __init__(self):
        self.influencer = None
        self._deep_runs: list[models.DeepAnalysisRun] = []
        self._deep_reports: list[models.DeepAnalysisReport] = []
        self.added: list = []
        self.committed = False

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        self.added.append(obj)
        if isinstance(obj, models.DeepAnalysisRun):
            self._deep_runs.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    def query(self, model):
        if model is models.DeepAnalysisRun:
            return FakeDeepQuery(model, self._deep_runs)
        if model is models.DeepAnalysisReport:
            return FakeDeepQuery(model, self._deep_reports)
        if model is models.Influencer:
            return FakeDeepQuery(model, [self.influencer] if self.influencer else [])
        return FakeDeepQuery(model, [])

    def get(self, model_cls, pk):
        if model_cls is models.Influencer:
            return self.influencer
        if model_cls is models.DeepAnalysisRun:
            for run in self._deep_runs:
                if run.id == pk:
                    return run
        return None

    def close(self):
        return None


class DeepAnalysisAPITest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides.clear()
        self.session = FakeDBSession()

        def _override_get_db():
            yield self.session

        def _override_get_current_user(
            token=None, access_token=None, db=None
        ):
            mock = MagicMock()
            mock.id = uuid4()
            mock.email = "test@example.com"
            mock.password_hash = "x"
            mock.name = "Test User"
            mock.company_name = "Test Co"
            return mock

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = _override_get_current_user

        self.influencer_id = uuid4()
        self.campaign_id = uuid4()

        self.session.influencer = models.Influencer(
            id=self.influencer_id,
            canonical_name="Test Creator",
            platforms={"instagram": "https://instagram.com/test"},
        )

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    # ------------------------------------------------------------------
    # GET /latest
    # ------------------------------------------------------------------

    def test_get_latest_returns_fresh_false_when_no_run(self) -> None:
        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/latest?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["fresh"])
        self.assertIsNone(body["report"])

    def test_get_latest_returns_fresh_true_when_cache_valid(self) -> None:
        run = models.DeepAnalysisRun(
            id=uuid4(),
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
            cache_expires_at=datetime.now(UTC) + timedelta(minutes=30),
            completed_at=datetime.now(UTC),
        )
        report = models.DeepAnalysisReport(
            id=uuid4(),
            run_id=run.id,
            overall_grade="A",
            audience_sentiment=75.0,
            fake_engagement_risk=10.0,
            brand_safety_summary="ok",
            recommendation="Strong audience sentiment supports partnership.",
            confidence="High",
            report_payload={"creator_summary": {"name": "Test"}},
        )
        self.session._deep_runs = [run]
        self.session._deep_reports = [report]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/latest?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["fresh"])
        self.assertEqual(body["report"]["overall_grade"], "A")
        self.assertEqual(body["report"]["report_payload"]["creator_summary"]["name"], "Test")

    def test_get_latest_returns_fresh_false_when_cache_expired(self) -> None:
        run = models.DeepAnalysisRun(
            id=uuid4(),
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
            cache_expires_at=datetime.now(UTC) - timedelta(minutes=1),
            completed_at=datetime.now(UTC) - timedelta(minutes=31),
        )
        report = models.DeepAnalysisReport(
            id=uuid4(),
            run_id=run.id,
            overall_grade="B",
            audience_sentiment=60.0,
            fake_engagement_risk=20.0,
            confidence="Medium",
            report_payload={},
        )
        self.session._deep_runs = [run]
        self.session._deep_reports = [report]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/latest?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["fresh"])
        self.assertIsNone(body["report"])

    def test_get_latest_ignores_non_completed_runs(self) -> None:
        run = models.DeepAnalysisRun(
            id=uuid4(),
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="running",
            cache_expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        self.session._deep_runs = [run]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/latest?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["fresh"])

    def test_get_latest_404_for_missing_influencer(self) -> None:
        self.session.influencer = None
        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/latest?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # POST /deep-analysis
    # ------------------------------------------------------------------

    def test_post_returns_existing_fresh_report(self) -> None:
        run = models.DeepAnalysisRun(
            id=uuid4(),
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
            cache_expires_at=datetime.now(UTC) + timedelta(minutes=30),
            completed_at=datetime.now(UTC),
        )
        report = models.DeepAnalysisReport(
            id=uuid4(),
            run_id=run.id,
            overall_grade="A",
            audience_sentiment=80.0,
            fake_engagement_risk=5.0,
            recommendation="Strong audience sentiment supports partnership.",
            confidence="High",
            report_payload={"creator_summary": {"name": "Test Creator"}},
        )
        self.session._deep_runs = [run]
        self.session._deep_reports = [report]

        resp = self.client.post(
            f"/api/influencers/{self.influencer_id}/deep-analysis?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "completed")
        self.assertIn("report", body)
        self.assertEqual(body["report"]["overall_grade"], "A")

    def test_post_force_true_bypasses_existing_fresh_report(self) -> None:
        run = models.DeepAnalysisRun(
            id=uuid4(),
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
            cache_expires_at=datetime.now(UTC) + timedelta(minutes=30),
            completed_at=datetime.now(UTC),
        )
        report = models.DeepAnalysisReport(
            id=uuid4(),
            run_id=run.id,
            overall_grade="A",
            audience_sentiment=80.0,
            fake_engagement_risk=5.0,
            recommendation="Strong audience sentiment supports partnership.",
            confidence="High",
            report_payload={"creator_summary": {"name": "Test Creator"}},
        )
        self.session._deep_runs = [run]
        self.session._deep_reports = [report]

        with patch("backend.pipeline.tasks.deep.deep_analyze.delay") as mock_delay:
            resp = self.client.post(
                f"/api/influencers/{self.influencer_id}/deep-analysis?campaign_id={self.campaign_id}&force=true"
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "queued")
        self.assertNotEqual(body["run_id"], str(run.id))
        created = [o for o in self.session.added if isinstance(o, models.DeepAnalysisRun)]
        self.assertEqual(len(created), 1)
        mock_delay.assert_called_once()

    def test_post_queues_new_run_when_no_fresh_cache(self) -> None:
        with patch("backend.pipeline.tasks.deep.deep_analyze.delay") as mock_delay:
            resp = self.client.post(
                f"/api/influencers/{self.influencer_id}/deep-analysis?campaign_id={self.campaign_id}"
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "queued")
        self.assertIsNotNone(body["run_id"])
        self.assertTrue(self.session.committed)
        # Verify a DeepAnalysisRun was created
        created = [o for o in self.session.added if isinstance(o, models.DeepAnalysisRun)]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].status, "queued")
        self.assertEqual(created[0].report_version, "v1")
        self.assertEqual(created[0].requested_post_limit, 20)
        self.assertEqual(created[0].requested_comment_limit, 200)
        mock_delay.assert_called_once()

    def test_post_stale_report_triggers_new_run(self) -> None:
        stale_run = models.DeepAnalysisRun(
            id=uuid4(),
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
            cache_expires_at=datetime.now(UTC) - timedelta(minutes=1),
            completed_at=datetime.now(UTC) - timedelta(minutes=31),
        )
        stale_report = models.DeepAnalysisReport(
            id=uuid4(), run_id=stale_run.id, overall_grade="C",
            audience_sentiment=50.0, fake_engagement_risk=30.0,
            confidence="Medium", report_payload={},
        )
        self.session._deep_runs = [stale_run]
        self.session._deep_reports = [stale_report]

        with patch("backend.pipeline.tasks.deep.deep_analyze.delay") as mock_delay:
            resp = self.client.post(
                f"/api/influencers/{self.influencer_id}/deep-analysis?campaign_id={self.campaign_id}"
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "queued")

    def test_post_404_for_missing_influencer(self) -> None:
        self.session.influencer = None
        resp = self.client.post(
            f"/api/influencers/{self.influencer_id}/deep-analysis?campaign_id={self.campaign_id}"
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # GET /deep-analysis/{run_id} (polling)
    # ------------------------------------------------------------------

    def test_poll_returns_run_status(self) -> None:
        run_id = uuid4()
        run = models.DeepAnalysisRun(
            id=run_id,
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="running",
            collected_comment_count=42,
            provider_coverage={"instagram": "ok"},
        )
        self.session._deep_runs = [run]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/{run_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["collected_comment_count"], 42)
        self.assertEqual(body["provider_coverage"], {"instagram": "ok"})
        self.assertIsNone(body["report"])

    def test_poll_returns_report_when_completed(self) -> None:
        run_id = uuid4()
        run = models.DeepAnalysisRun(
            id=run_id,
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
            collected_comment_count=200,
        )
        report = models.DeepAnalysisReport(
            id=uuid4(),
            run_id=run_id,
            overall_grade="A",
            audience_sentiment=85.0,
            fake_engagement_risk=3.0,
            recommendation="Strong audience sentiment supports partnership.",
            confidence="High",
            report_payload={"creator_summary": {"name": "Test"}},
        )
        self.session._deep_runs = [run]
        self.session._deep_reports = [report]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/{run_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "completed")
        self.assertIsNotNone(body["report"])
        self.assertEqual(body["report"]["overall_grade"], "A")

    def test_poll_returns_failure_reason_when_failed(self) -> None:
        run_id = uuid4()
        run = models.DeepAnalysisRun(
            id=run_id,
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="failed",
            failure_reason="Instagram API rate limit exceeded",
        )
        self.session._deep_runs = [run]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/{run_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["failure_reason"], "Instagram API rate limit exceeded")

    def test_poll_404_for_missing_run(self) -> None:
        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/deep-analysis/{uuid4()}"
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # GET /reports/{report_id}
    # ------------------------------------------------------------------

    def test_get_report_returns_full_payload(self) -> None:
        run_id = uuid4()
        report_id = uuid4()
        run = models.DeepAnalysisRun(
            id=run_id,
            campaign_id=self.campaign_id,
            influencer_id=self.influencer_id,
            status="completed",
        )
        report = models.DeepAnalysisReport(
            id=report_id,
            run_id=run_id,
            overall_grade="A",
            audience_sentiment=82.0,
            fake_engagement_risk=8.0,
            brand_safety_summary="No issues flagged.",
            recommendation="Strong audience sentiment supports partnership.",
            confidence="High",
            report_payload={
                "creator_summary": {"name": "Test Creator"},
                "platform_coverage": {"instagram": {"profile_status": "ok", "posts": 15}},
                "comments_analyzed": 300,
                "key_strengths": ["Strong positive audience sentiment"],
                "key_risks": [],
                "citations": [{"source": "post", "post_id": "abc"}],
            },
        )
        self.session._deep_runs = [run]
        self.session._deep_reports = [report]

        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/reports/{report_id}"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["overall_grade"], "A")
        self.assertEqual(body["confidence"], "High")
        self.assertTrue(isinstance(body["report_payload"], dict))
        self.assertEqual(body["report_payload"]["comments_analyzed"], 300)

    def test_get_report_404_when_not_found(self) -> None:
        resp = self.client.get(
            f"/api/influencers/{self.influencer_id}/reports/{uuid4()}"
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
