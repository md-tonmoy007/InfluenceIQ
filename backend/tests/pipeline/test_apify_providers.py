"""Tests for Apify-backed platform profile providers."""

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

from backend.pipeline.content.providers.tiktok import fetch_tiktok_profile
from backend.pipeline.content.providers.x import fetch_x_profile


class ApifyPlatformProviderTest(unittest.TestCase):
    def test_tiktok_uses_apify_when_configured(self) -> None:
        apify_item = {
            "authorMeta": {
                "uniqueId": "mayatrails",
                "nickName": "Maya Trails",
                "signature": "Outdoor creator",
                "fans": 88000,
                "heart": 1200000,
                "verified": True,
            },
            "videos": [{"desc": "Trail gear review", "playCount": 5000}],
        }
        with (
            patch("backend.pipeline.content.providers.tiktok.settings.APIFY_API_TOKEN", "token"),
            patch(
                "backend.pipeline.content.providers.tiktok.run_actor_sync",
                return_value=apify_item,
            ),
        ):
            profile = fetch_tiktok_profile("https://www.tiktok.com/@mayatrails")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.provider, "apify_tiktok")
        self.assertEqual(profile.followers, 88000)
        self.assertEqual(profile.handle, "mayatrails")
        self.assertEqual(len(profile.posts), 1)

    def test_x_uses_apify_when_configured(self) -> None:
        apify_item = {
            "userName": "mayatrails",
            "name": "Maya Trails",
            "description": "Outdoor creator and gear reviewer",
            "followers": 88000,
            "following": 300,
            "isVerified": True,
            "tweets": [{"text": "Great trail run today", "likeCount": 120}],
        }
        with (
            patch("backend.pipeline.content.providers.x.settings.APIFY_API_TOKEN", "token"),
            patch(
                "backend.pipeline.content.providers.x.run_actor_sync",
                return_value=apify_item,
            ),
        ):
            profile = fetch_x_profile("https://twitter.com/mayatrails")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.provider, "apify_x")
        self.assertEqual(profile.followers, 88000)
        self.assertEqual(profile.following, 300)
        self.assertTrue(profile.verified)


if __name__ == "__main__":
    unittest.main()
