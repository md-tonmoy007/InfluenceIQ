"""Contract tests for the YouTube provider's optional Data API v3 path.

Covers the three scenarios in plan 06 §5.1:

1. No YOUTUBE_API_KEY → HTML regex + RSS path (failure-mode parity).
2. With YOUTUBE_API_KEY and channels.list returning a populated item →
   authoritative stats, verified badge, lifetime_views populated.
3. With YOUTUBE_API_KEY and channels.list returning an empty items list
   → graceful fallback to the HTML path with provider="youtube_html_fallback".
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


def _set_youtube_key(key: str) -> None:
    """Force ``settings.YOUTUBE_API_KEY`` to ``key`` for the duration of a test.

    The youtube provider imports ``settings`` by name at module load
    time, so simply re-binding ``config.settings`` is not enough — the
    module's local reference would still point at the old object. We
    rebind both: a fresh ``Settings`` instance onto ``config.settings``
    AND the same instance onto the provider module's ``settings``
    attribute so the provider's reads see the updated value.
    """
    from backend.core import config as config_module
    from backend.pipeline.content.providers import youtube as youtube_module

    fresh = config_module.Settings(YOUTUBE_API_KEY=key)
    config_module.settings = fresh
    youtube_module.settings = fresh


class _DummyResponse:
    def __init__(self, text: str = "", json_payload: dict | None = None) -> None:
        self.text = text
        self.content = text
        self.status_code = 200
        self._json_payload = json_payload
        self.headers = {"content-type": "text/html"}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._json_payload or {}


HTML = """
<html><head>
  <meta property="og:title" content="Trail Coach - YouTube">
  <meta name="description" content="124K subscribers. Certified trail running coach.">
  <meta itemprop="channelId" content="UC123">
</head><body>Verified</body></html>
"""

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
  <entry>
    <yt:videoId>v1</yt:videoId>
    <title>Trail gear review</title>
    <published>2026-01-01T00:00:00+00:00</published>
    <media:group><media:description>Helpful authentic comments</media:description></media:group>
  </entry>
  <entry>
    <yt:videoId>v2</yt:videoId>
    <title>Trail nutrition</title>
    <published>2025-12-15T00:00:00+00:00</published>
    <media:group><media:description>Evidence based advice</media:description></media:group>
  </entry>
</feed>
"""

CHANNELS_ITEM = {
    "id": "UC123",
    "statistics": {
        "subscriberCount": "500000",
        "viewCount": "12000000",
        "videoCount": "200",
    },
    "snippet": {
        "title": "Trail Coach",
        "description": "Certified trail running coach helping outdoor athletes.",
        "customUrl": "@trail",
    },
    "status": {"isLinked": True},
}

VIDEOS_PAYLOAD = {
    "items": [
        {
            "id": "v1",
            "statistics": {
                "viewCount": "15000",
                "likeCount": "900",
                "commentCount": "55",
            },
        },
        {
            "id": "v2",
            "statistics": {
                "viewCount": "8000",
                "likeCount": "400",
                "commentCount": "30",
            },
        },
    ],
}


def _fake_get_factory(*, channels_payload: dict | None):
    """Patch ``httpx.get`` so HTML/RSS path is identical across scenarios,
    and the YouTube Data API v3 endpoints return the supplied fixture."""

    def fake_get(url: str, *args, **kwargs):
        if "feeds/videos.xml" in url:
            return _DummyResponse(RSS)
        if "googleapis.com/youtube/v3/channels" in url:
            return _DummyResponse(json_payload=channels_payload or {"items": []})
        if "googleapis.com/youtube/v3/videos" in url:
            return _DummyResponse(json_payload=VIDEOS_PAYLOAD)
        return _DummyResponse(HTML)

    return fake_get


class YouTubeProviderContractTest(unittest.TestCase):
    def setUp(self) -> None:
        # Always start from a clean "no key" baseline; per-test overrides come next.
        _set_youtube_key("")

    def test_no_key_uses_html_regex_and_rss(self) -> None:
        from backend.pipeline.content.providers.youtube import fetch_youtube_profile

        with (
            patch(
                "backend.pipeline.content.providers.youtube.httpx.get",
                side_effect=_fake_get_factory(channels_payload=None),
            ),
        ):
            profile = fetch_youtube_profile("https://www.youtube.com/@trailcoach")

        self.assertIsNotNone(profile)
        # 124K from og:description "124K subscribers"
        self.assertEqual(profile.followers, 124_000)
        # "Verified" substring match wins
        self.assertTrue(profile.verified)
        # No API path → no lifetime_views
        self.assertNotIn("lifetime_views", profile.raw or {})
        # No API path → posts lack view_count
        self.assertTrue(all("view_count" not in p for p in profile.posts))
        self.assertEqual(profile.provider, "youtube")

    def test_with_key_and_populated_channels_uses_api(self) -> None:
        from backend.pipeline.content.providers.youtube import fetch_youtube_profile

        _set_youtube_key("test_key")
        try:
            with patch(
                "backend.pipeline.content.providers.youtube.httpx.get",
                side_effect=_fake_get_factory(channels_payload={"items": [CHANNELS_ITEM]}),
            ):
                profile = fetch_youtube_profile("https://www.youtube.com/@trailcoach")
        finally:
            _set_youtube_key("")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.followers, 500_000)
        self.assertTrue(profile.verified)
        self.assertEqual(profile.raw.get("lifetime_views"), 12_000_000)
        self.assertEqual(profile.raw.get("api_source"), "youtube_data_v3")
        # Per-video stats should land on each post
        view_counts = sorted(p.get("view_count") for p in profile.posts)
        self.assertEqual(view_counts, [8_000, 15_000])
        self.assertEqual(profile.provider, "youtube")

    def test_with_key_but_empty_channels_falls_back_to_html(self) -> None:
        from backend.pipeline.content.providers.youtube import fetch_youtube_profile

        _set_youtube_key("test_key")
        try:
            with patch(
                "backend.pipeline.content.providers.youtube.httpx.get",
                side_effect=_fake_get_factory(channels_payload={"items": []}),
            ):
                profile = fetch_youtube_profile("https://www.youtube.com/@trailcoach")
        finally:
            _set_youtube_key("")

        self.assertIsNotNone(profile)
        # HTML regex + RSS path with the "key set but no data" provider tag
        self.assertEqual(profile.provider, "youtube_html_fallback")
        self.assertEqual(profile.followers, 124_000)
        self.assertTrue(profile.verified)
        self.assertNotIn("api_source", profile.raw or {})


if __name__ == "__main__":
    unittest.main()
