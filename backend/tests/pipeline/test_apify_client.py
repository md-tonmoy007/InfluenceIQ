"""Tests for the shared Apify client helpers."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.core.config import settings
from backend.pipeline.content.providers.apify_client import (
    pick_first_item,
    run_actor_sync,
    run_actor_sync_all,
)


class _DummyResponse:
    def __init__(self, json_payload, status_code: int = 200) -> None:
        self._json_payload = json_payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self) -> dict | list:
        return self._json_payload


class RunActorSyncAllTest(unittest.TestCase):
    def test_returns_full_dataset(self) -> None:
        dataset = [{"cid": "c1"}, {"cid": "c2"}, {"cid": "c3"}]

        def fake_post(url: str, *args, **kwargs):
            return _DummyResponse(json_payload=dataset)

        with (
            patch.object(settings, "APIFY_API_TOKEN", "token"),
            patch("backend.pipeline.content.providers.apify_client.httpx.post", side_effect=fake_post),
        ):
            items = run_actor_sync_all("actor/comment-scraper", [{"postURLs": ["u"]}])

        self.assertEqual(len(items), 3)
        self.assertEqual([i["cid"] for i in items], ["c1", "c2", "c3"])

    def test_unwraps_nested_dataset_keys(self) -> None:
        dataset = {"items": [{"cid": "c1"}, {"cid": "c2"}]}

        def fake_post(url: str, *args, **kwargs):
            return _DummyResponse(json_payload=dataset)

        with (
            patch.object(settings, "APIFY_API_TOKEN", "token"),
            patch("backend.pipeline.content.providers.apify_client.httpx.post", side_effect=fake_post),
        ):
            items = run_actor_sync_all("actor/comment-scraper", [{"postURLs": ["u"]}])

        self.assertEqual(len(items), 2)

    def test_empty_token_returns_empty(self) -> None:
        with patch.object(settings, "APIFY_API_TOKEN", ""):
            self.assertEqual(run_actor_sync_all("actor", []), [])

    def test_run_actor_sync_behavior_unchanged(self) -> None:
        profile = {"username": "creator", "followers": 1000}

        def fake_post(url: str, *args, **kwargs):
            return _DummyResponse(json_payload=[profile, {"username": "other"}])

        with (
            patch.object(settings, "APIFY_API_TOKEN", "token"),
            patch("backend.pipeline.content.providers.apify_client.httpx.post", side_effect=fake_post),
        ):
            item = run_actor_sync("actor/profile-scraper", [{}], username="creator")

        self.assertEqual(item, profile)

    def test_total_budget_caps_attempts(self) -> None:
        """timeout is a TOTAL budget: exhausting it stops trying more payloads.

        Each attempt burns the whole per-attempt cap (simulating a slow actor),
        so six wrong-shape payloads must NOT run six full timeouts — the budget
        bounds how many attempts fire before we give up. This is the fix that
        stops one influencer from pinning a worker for minutes.
        """
        clock = {"t": 1000.0}
        calls = {"n": 0}

        def fake_monotonic() -> float:
            return clock["t"]

        def fake_post(url: str, *args, **kwargs):
            calls["n"] += 1
            # Simulate each attempt consuming its full allotted timeout.
            clock["t"] += kwargs["timeout"]
            raise RuntimeError("actor slow / wrong shape")

        payloads = [{"a": i} for i in range(6)]
        with (
            patch.object(settings, "APIFY_API_TOKEN", "token"),
            patch("backend.pipeline.content.providers.apify_client.time.monotonic", side_effect=fake_monotonic),
            patch("backend.pipeline.content.providers.apify_client.httpx.post", side_effect=fake_post),
        ):
            # total budget 100s, per-attempt cap 45s -> at most 3 attempts fit.
            with self.assertRaises(RuntimeError):
                run_actor_sync("actor/profile-scraper", payloads, timeout=100)

        self.assertLess(calls["n"], len(payloads))
        self.assertLessEqual(calls["n"], 3)


class PickFirstItemTest(unittest.TestCase):
    def test_dict_payload(self) -> None:
        self.assertEqual(pick_first_item({"username": "x"}), {"username": "x"})

    def test_list_payload(self) -> None:
        self.assertEqual(pick_first_item([{"a": 1}, {"b": 2}]), {"a": 1})

    def test_username_match(self) -> None:
        items = [{"username": "aaa"}, {"username": "bbb"}]
        self.assertEqual(pick_first_item(items, username="bbb"), {"username": "bbb"})


if __name__ == "__main__":
    unittest.main()
