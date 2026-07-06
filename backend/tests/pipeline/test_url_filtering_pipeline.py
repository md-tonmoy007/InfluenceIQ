"""Tests for fail-closed URL filtering and rejected-source visibility.

Covers the Plan 03 behavior:
* :func:`execute_search` persists rejected results as
  ``CrawlSource(status="rejected", error_message=reason)`` and does
  NOT fan them out to ``fetch_page.delay``.
* The emitted ``search.executed`` payload carries a ``rejected`` list
  matching the persisted rows.
* :func:`refresh_campaign_status` resolves an all-rejected campaign
  to ``"failed"`` rather than leaving it stuck on ``"running"``.
"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


def _model_key(model: object) -> str:
    """Return a stable lookup key for either a model class or a Column."""
    cls = getattr(model, "class_", None)  # SQLAlchemy Column
    if cls is not None:
        return cls.__name__
    name = getattr(model, "__name__", None)
    return name or str(model)


class _ScriptedQuery:
    """Records call order per-model so successive `.count()`/`.all()`
    calls on the same model return scripted values."""

    def __init__(self, key: str, counts: dict, listings: dict) -> None:
        self._key = key
        self._counts = counts
        self._listings = listings

    def filter(self, *args, **kwargs) -> _ScriptedQuery:
        return self

    def join(self, *args, **kwargs) -> _ScriptedQuery:
        return self

    def distinct(self) -> _ScriptedQuery:
        return self

    def count(self) -> int:
        seq = self._counts.setdefault(self._key, [])
        if not seq:
            return 0
        return seq.pop(0)

    def all(self) -> list:
        return self._listings.get(self._key, [])


class _ScriptedSession:
    def __init__(self, campaign, counts: dict, listings: dict) -> None:
        self._campaign = campaign
        self._counts = counts
        self._listings = listings

    def get(self, model, pk):
        from backend.core.database import models
        if model is models.Campaign:
            return self._campaign
        return None

    def query(self, model):
        return _ScriptedQuery(_model_key(model), self._counts, self._listings)


class _FirstNoneSession:
    """A minimal session for execute_search: tracks .add() calls and
    returns None from .query(...).first() so a new row is always
    created."""

    def __init__(self) -> None:
        self.added: list = []

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        import uuid
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                try:
                    obj.id = uuid.uuid4()
                except (AttributeError, TypeError):
                    pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def get(self, model, pk) -> None:
        return None

    def query(self, model):
        class _Q:
            def filter(self, *a, **k) -> _Q:
                return self

            def first(self):
                return None

        return _Q()


@contextmanager
def _ctx(session):
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class ExecuteSearchRejectionTest(unittest.TestCase):
    def test_rejected_results_persisted_and_not_fanned_out(self) -> None:
        from backend.pipeline.tasks import search as search_mod
        from backend.pipeline.tasks.search import execute_search

        campaign_id = "11111111-1111-1111-1111-111111111111"

        search_results = [
            {"url": "https://example.com/keep", "title": "Keep", "snippet": "bio"},
            {"url": "https://example.com/drop", "title": "Drop", "snippet": "shop"},
        ]
        accepted = [search_results[0]]
        rejected = [{**search_results[1], "reason": "not_selected"}]

        session = _FirstNoneSession()

        with patch.object(search_mod, "db_session", lambda: _ctx(session)), \
             patch.object(search_mod, "search_web", return_value=search_results), \
             patch.object(search_mod, "get_campaign", return_value=MagicMock(
                 id=campaign_id,
                 search_query="vegan protein",
                 preferred_platforms=["youtube"],
                 brief_snapshot={},
             )), \
             patch.object(search_mod, "campaign_query_payload", return_value={"description": "x"}), \
             patch.object(search_mod, "_llm_filter_urls", return_value=(accepted, rejected)), \
             patch.object(search_mod, "refresh_campaign_status") as refresh, \
             patch.object(search_mod, "publish_event") as publish, \
             patch.object(search_mod, "set_phase") as set_phase, \
             patch("backend.pipeline.tasks.crawl.fetch_page") as fetch_page:
            result = execute_search.apply(
                args=[campaign_id, "vegan protein", 0]
            ).get()

        # Rejected row persisted with status="rejected" + error_message=reason.
        rejected_rows = [r for r in session.added if getattr(r, "status", None) == "rejected"]
        self.assertEqual(len(rejected_rows), 1)
        row = rejected_rows[0]
        self.assertEqual(row.url, "https://example.com/drop")
        self.assertEqual(row.error_message, "not_selected")

        # Accepted row persisted as pending.
        pending_rows = [r for r in session.added if getattr(r, "status", None) == "pending"]
        self.assertEqual(len(pending_rows), 1)
        self.assertEqual(pending_rows[0].url, "https://example.com/keep")

        # fetch_page.delay called once (for the accepted source only).
        self.assertEqual(fetch_page.delay.call_count, 1)
        self.assertIn(campaign_id, fetch_page.delay.call_args.args)

        # refresh_campaign_status was invoked once.
        refresh.assert_called_once_with(session, campaign_id)

        # search.executed payload carries the rejected list.
        self.assertEqual(publish.call_args.args[1], "search.executed")
        payload = publish.call_args.kwargs
        self.assertEqual(
            payload["rejected"],
            [{"url": "https://example.com/drop", "reason": "not_selected"}],
        )
        self.assertEqual(payload["result_count"], 1)

        # Task return value mirrors the rejected list.
        self.assertEqual(result["rejected"], payload["rejected"])

        # set_phase counts only accepted URLs.
        set_phase.assert_called_once_with(campaign_id, urls_discovered=1)


class RefreshCampaignStatusAllRejectedTest(unittest.TestCase):
    def test_all_rejected_campaign_resolves_to_failed(self) -> None:
        """A campaign whose every CrawlSource is `rejected` ends `failed`."""
        from backend.pipeline.tasks import _common as common

        campaign_id = "22222222-2222-2222-2222-222222222222"
        campaign = MagicMock(
            id=campaign_id,
            status="running",
            failed_at=None,
            completed_at=None,
            failure_reason=None,
        )

        # refresh_campaign_status call order on CrawlSource:
        #   1) total_sources  -> 2
        #   2) pending_sources -> 0
        #   3) failed_sources -> 2 (folded rejected bucket)
        # InfluencerScore.distinct().count() -> 0 (no scores)
        # CrawlSourceInfluencer & CrawlSource listings -> []  (no influencers)
        counts: dict = {
            "CrawlSource": [2, 0, 2],
            "InfluencerScore": [0],
        }
        listings: dict = {
            "CrawlSourceInfluencer": [],
            "CrawlSource": [],
        }
        session = _ScriptedSession(campaign, counts, listings)

        with patch.object(common, "emit_campaign_lifecycle_event") as emit:
            common.refresh_campaign_status(session, campaign_id)

        self.assertEqual(campaign.status, "failed")
        emit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
