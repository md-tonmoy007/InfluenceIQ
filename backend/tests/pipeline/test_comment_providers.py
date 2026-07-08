"""Tests for real audience-comment fetchers."""

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
from backend.pipeline.content.providers.comments.base import (
    fetch_post_comments,
)
from backend.pipeline.content.providers.comments.instagram import (
    fetch_instagram_post_comments,
)
from backend.pipeline.content.providers.comments.tiktok import (
    fetch_tiktok_post_comments,
)
from backend.pipeline.content.providers.comments.youtube import (
    fetch_youtube_post_comments,
)


class _DummyResponse:
    def __init__(self, json_payload: dict | None = None, status_code: int = 200) -> None:
        self.status_code = status_code
        self._json_payload = json_payload or {}
        self.text = str(json_payload) if json_payload else ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self) -> dict:
        return self._json_payload


class YouTubeCommentProviderTest(unittest.TestCase):
    def test_fetch_maps_comment_threads(self) -> None:
        payload = {
            "items": [
                {
                    "id": "c1",
                    "snippet": {
                        "topLevelComment": {
                            "snippet": {
                                "textOriginal": "Great video!",
                                "authorChannelId": {"value": "UCAUTHOR1"},
                                "likeCount": 12,
                                "publishedAt": "2026-01-01T12:00:00Z",
                            }
                        },
                        "totalReplyCount": 3,
                    },
                },
                {
                    "id": "c2",
                    "snippet": {
                        "topLevelComment": {
                            "snippet": {
                                "textDisplay": "Thanks for sharing",
                                "authorDisplayName": "fan2",
                                "likeCount": 4,
                                "publishedAt": "2026-01-01T13:00:00+00:00",
                            }
                        },
                        "totalReplyCount": 0,
                    },
                },
            ]
        }

        def fake_get(url: str, *args, **kwargs):
            self.assertIn("/commentThreads", url)
            return _DummyResponse(json_payload=payload)

        with (
            patch.object(settings, "YOUTUBE_API_KEY", "test-key"),
            patch("backend.pipeline.content.providers.comments.youtube.httpx.get", side_effect=fake_get),
            patch("backend.pipeline.content.providers.comments.youtube.get_cached_youtube_api", return_value=None),
            patch("backend.pipeline.content.providers.comments.youtube.store_cached_youtube_api"),
        ):
            comments = fetch_youtube_post_comments("v123", 50)

        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].external_id, "c1")
        self.assertEqual(comments[0].text, "Great video!")
        self.assertEqual(comments[0].author_key, "UCAUTHOR1")
        self.assertEqual(comments[0].like_count, 12)
        self.assertEqual(comments[0].reply_count, 3)
        self.assertIsNotNone(comments[0].published_at)

    def test_comments_disabled_returns_empty_list(self) -> None:
        def fake_get(url: str, *args, **kwargs):
            return _DummyResponse(
                json_payload={"error": {"errors": [{"reason": "commentsDisabled"}]}},
                status_code=403,
            )

        with (
            patch.object(settings, "YOUTUBE_API_KEY", "test-key"),
            patch("backend.pipeline.content.providers.comments.youtube.httpx.get", side_effect=fake_get),
            patch("backend.pipeline.content.providers.comments.youtube.get_cached_youtube_api", return_value=None),
        ):
            comments = fetch_youtube_post_comments("vDisabled", 50)

        self.assertEqual(comments, [])

    def test_uses_cache_when_available(self) -> None:
        cached = [
            {
                "external_id": "cached1",
                "text": "Cached comment",
                "author_key": "UCA",
                "like_count": 1,
                "published_at": "2026-01-01T00:00:00+00:00",
                "reply_count": 0,
            }
        ]

        with (
            patch.object(settings, "YOUTUBE_API_KEY", "test-key"),
            patch("backend.pipeline.content.providers.comments.youtube.httpx.get") as mock_get,
            patch("backend.pipeline.content.providers.comments.youtube.get_cached_youtube_api", return_value=cached),
        ):
            comments = fetch_youtube_post_comments("vCache", 50)

        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].external_id, "cached1")
        mock_get.assert_not_called()


class ApifyCommentProviderTest(unittest.TestCase):
    def test_instagram_maps_actor_items(self) -> None:
        items = [
            {
                "id": "ig1",
                "text": "Love this post!",
                "ownerUsername": "fan_a",
                "likesCount": 7,
                "timestamp": "2026-01-02T10:00:00Z",
            },
            {
                "id": "ig2",
                "text": "Nice shot",
                "owner": {"username": "fan_b"},
                "likesCount": 2,
                "timestamp": 1735812000,
            },
        ]

        with (
            patch.object(settings, "APIFY_API_TOKEN", "token"),
            patch(
                "backend.pipeline.content.providers.comments.instagram.run_actor_sync_all",
                return_value=items,
            ),
        ):
            comments = fetch_instagram_post_comments("https://instagram.com/p/abc", 10)

        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].external_id, "ig1")
        self.assertEqual(comments[0].author_key, "fan_a")
        self.assertEqual(comments[0].like_count, 7)
        self.assertIsNotNone(comments[1].published_at)

    def test_tiktok_maps_actor_items(self) -> None:
        items = [
            {
                "cid": "tk1",
                "text": "fire #trending",
                "uniqueId": "fan_one",
                "diggCount": 15,
                "createTimeISO": "2026-01-03T08:00:00Z",
                "replyCount": 1,
            },
            {
                "id": "tk2",
                "text": "lol",
                "user": {"uniqueId": "fan_two"},
                "createTime": 1735891200,
            },
        ]

        with (
            patch.object(settings, "APIFY_API_TOKEN", "token"),
            patch(
                "backend.pipeline.content.providers.comments.tiktok.run_actor_sync_all",
                return_value=items,
            ),
        ):
            comments = fetch_tiktok_post_comments("https://tiktok.com/@user/video/1", 10)

        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].external_id, "tk1")
        self.assertEqual(comments[0].text, "fire #trending")
        self.assertEqual(comments[0].author_key, "fan_one")
        self.assertEqual(comments[0].like_count, 15)
        self.assertEqual(comments[0].reply_count, 1)


class CommentDispatchTest(unittest.TestCase):
    def test_unsupported_platform_returns_empty(self) -> None:
        self.assertEqual(fetch_post_comments("x", "https://x.com/post", "p1", 10), [])

    def test_circuit_open_returns_empty(self) -> None:
        with patch("backend.pipeline.content.providers.comments.base.provider_is_available", return_value=False):
            self.assertEqual(fetch_post_comments("youtube", "", "v1", 10), [])

    def test_fetch_failure_degrades_to_empty(self) -> None:
        with (
            patch("backend.pipeline.content.providers.comments.base.provider_is_available", return_value=True),
            patch(
                "backend.pipeline.content.providers.comments.youtube.fetch_youtube_post_comments",
                side_effect=RuntimeError("boom"),
            ),
            patch("backend.pipeline.content.providers.comments.base.record_provider_failure") as mock_record,
        ):
            result = fetch_post_comments("youtube", "", "v1", 10)
        self.assertEqual(result, [])
        mock_record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
