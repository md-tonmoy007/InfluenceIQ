"""Tests for the YouTube provider's YOUTUBE_API_KEY wiring (Plan 06 / Strand A).

The provider reads ``settings.YOUTUBE_API_KEY`` from the shared settings
object. When the key is empty the provider falls back to the HTML regex
path with the "Verified" substring match. When the key is set and the
``channels.list`` / ``videos.list`` calls return data, the profile
carries authoritative ``followers``, ``lifetime_views``, the
``verified`` flag derived from ``status.isLinked`` + ``customUrl``, and
per-post ``view_count`` / ``like_count`` / ``comment_count``.

These tests do not call Google. They patch the module's
``httpx.get`` and inject canned HTML + RSS + API JSON. The settings
singleton is patched in place via ``patch.object(settings, ...)`` so
the provider reads the test value on the next call.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch  # noqa: F401  (used as `patch(...)` and `patch.object(...)` below)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.core.config import settings  # noqa: E402
from backend.pipeline.content.providers.youtube import (  # noqa: E402
    fetch_youtube_profile,
)


class _DummyResponse:
    def __init__(self, text: str = "", json_payload: dict | None = None, status_code: int = 200) -> None:
        self.text = text
        self.content = text
        self.status_code = status_code
        self._json_payload = json_payload
        self.headers = {"content-type": "text/html" if not json_payload else "application/json"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self) -> dict:
        return self._json_payload or {}


_HTML = """
    <html><head>
      <meta property="og:title" content="Trail Coach - YouTube">
      <meta name="description" content="124K subscribers. Certified trail running coach.">
      <meta itemprop="channelId" content="UC123">
    </head><body>Verified</body></html>
"""

_RSS = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:yt="http://www.youtube.com/xml/schemas/2015"
          xmlns:media="http://search.yahoo.com/mrss/">
      <entry><yt:videoId>v1</yt:videoId><title>Trail gear review</title>
      <published>2026-01-01T00:00:00+00:00</published>
      <media:group><media:description>Helpful authentic comments</media:description></media:group></entry>
      <entry><yt:videoId>v2</yt:videoId><title>Shoe breakdown</title>
      <published>2025-12-15T00:00:00+00:00</published>
      <media:group><media:description>Field test notes</media:description></media:group></entry>
    </feed>
"""


class YouTubeProviderEnvWiringTest(unittest.TestCase):
    def test_no_key_falls_back_to_html_regex(self) -> None:
        """No key → no API calls, HTML regex, "Verified" substring match."""

        def fake_get(url: str, *args, **kwargs):
            if "feeds/videos.xml" in url:
                return _DummyResponse(_RSS)
            return _DummyResponse(_HTML)

        with (
            patch.object(settings, "YOUTUBE_API_KEY", ""),
            patch("backend.pipeline.content.providers.youtube.httpx.get", side_effect=fake_get),
        ):
            profile = fetch_youtube_profile("https://www.youtube.com/@trailcoach")

        self.assertIsNotNone(profile)
        assert profile is not None
        # compact_number parses "124K subscribers" out of the description.
        self.assertEqual(profile.followers, 124000)
        # No API call → no lifetime_views key on raw, no per-post view_count.
        self.assertNotIn("lifetime_views", profile.raw)
        for post in profile.posts:
            self.assertNotIn("view_count", post)
        # HTML substring match picks up "Verified" in the body.
        self.assertTrue(profile.verified)
        # provider is the bare "youtube" tag (no key → no _html_fallback suffix).
        self.assertEqual(profile.provider, "youtube")

    def test_with_key_uses_channels_api(self) -> None:
        """Key set + channels.list returns a hit → authoritative stats."""

        channels_payload = {
            "items": [
                {
                    "id": "UC123",
                    "statistics": {
                        "subscriberCount": "500000",
                        "viewCount": "12000000",
                        "videoCount": "142",
                    },
                    "snippet": {
                        "title": "Trail Coach",
                        "description": "Authoritative bio from the API.",
                        "customUrl": "@trail",
                    },
                    "status": {"isLinked": True},
                }
            ]
        }
        videos_payload = {
            "items": [
                {
                    "id": "v1",
                    "statistics": {
                        "viewCount": "18000",
                        "likeCount": "1200",
                        "commentCount": "55",
                    },
                },
                {
                    "id": "v2",
                    "statistics": {
                        "viewCount": "9000",
                        "likeCount": "600",
                        "commentCount": "20",
                    },
                },
            ]
        }

        def fake_get(url: str, *args, **kwargs):
            if "feeds/videos.xml" in url:
                return _DummyResponse(_RSS)
            if "/youtube/v3/channels" in url:
                return _DummyResponse(json_payload=channels_payload)
            if "/youtube/v3/videos" in url:
                return _DummyResponse(json_payload=videos_payload)
            return _DummyResponse(_HTML)

        with (
            patch.object(settings, "YOUTUBE_API_KEY", "test-key"),
            patch("backend.pipeline.content.providers.youtube.httpx.get", side_effect=fake_get),
        ):
            profile = fetch_youtube_profile("https://www.youtube.com/@trailcoach")

        self.assertIsNotNone(profile)
        assert profile is not None
        # Authoritative subscriber count from channels.list.
        self.assertEqual(profile.followers, 500000)
        self.assertTrue(profile.verified)
        self.assertEqual(profile.raw.get("lifetime_views"), 12_000_000)
        self.assertEqual(profile.raw.get("api_source"), "youtube_data_v3")
        # Per-post stats from videos.list populate the engagement roll-up inputs.
        views = sorted(p["view_count"] for p in profile.posts)
        self.assertEqual(views, [9000, 18000])
        for post in profile.posts:
            self.assertIn("like_count", post)
            self.assertIn("comment_count", post)
        # API path keeps the bare "youtube" provider tag.
        self.assertEqual(profile.provider, "youtube")

    def test_with_key_but_channels_empty_falls_back(self) -> None:
        """Key set + channels.list returns no items → falls back to HTML path."""

        empty_channels = {"items": []}

        def fake_get(url: str, *args, **kwargs):
            if "feeds/videos.xml" in url:
                return _DummyResponse(_RSS)
            if "/youtube/v3/channels" in url:
                return _DummyResponse(json_payload=empty_channels)
            if "/youtube/v3/videos" in url:
                return _DummyResponse(json_payload={"items": []})
            return _DummyResponse(_HTML)

        with (
            patch.object(settings, "YOUTUBE_API_KEY", "test-key"),
            patch("backend.pipeline.content.providers.youtube.httpx.get", side_effect=fake_get),
        ):
            profile = fetch_youtube_profile("https://www.youtube.com/@trailcoach")

        self.assertIsNotNone(profile)
        assert profile is not None
        # Empty API result → HTML regex, no lifetime_views.
        self.assertEqual(profile.followers, 124000)
        self.assertNotIn("lifetime_views", profile.raw)
        # Provider label exposes that the key was set but the API was empty.
        self.assertEqual(profile.provider, "youtube_html_fallback")


if __name__ == "__main__":
    unittest.main()
