from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from app.pipeline import (
    _apply_profile_enrichment,
    _build_sub_scores,
    _get_or_create_influencer,
    _merge_mention,
)


class HybridPipelineTest(unittest.TestCase):
    def test_direct_profile_overrides_article_mention_fields(self) -> None:
        by_identity = {}
        identity = {
            "platform": "youtube",
            "canonical_profile_url": "https://youtube.com/@coachmaya",
            "handle_or_username": "coachmaya",
            "channel_id": None,
        }
        influencer = _get_or_create_influencer(by_identity, identity)
        _merge_mention(
            influencer,
            {
                "name": "Coach Maya",
                "handle": "",
                "platform": "youtube",
                "platforms": {"youtube": "https://youtube.com/@coachmaya"},
                "credentials": ["Certified Coach"],
                "source_url": "https://example.org/feature",
                "context": "Coach Maya is a certified trail coach and creator.",
            },
            {"url": "https://example.org/feature", "title": "Feature", "metadata": {}},
            {"url": "https://example.org/feature", "provider": "scrape.do", "attempt_count": 1, "archive_fallback_used": False, "domain": "example.org", "rate_limited": False, "depth": 1, "source_type": "search_result", "parent_url": ""},
            {"url": "https://example.org/feature"},
            {"reasons": []},
        )
        _apply_profile_enrichment(
            influencer,
            {
                "platform": "youtube",
                "identity": identity,
                "name": "Coach Maya Official",
                "handle": "coachmaya",
                "followers": 44000,
                "engagement_rate": 0.065,
                "source_payload": {"verified": True, "engagement": {"sample_size": 10}},
            },
            {"url": "https://youtube.com/@coachmaya"},
            {"url": "https://youtube.com/@coachmaya", "provider": "scrape.do", "attempt_count": 1, "archive_fallback_used": False, "domain": "youtube.com", "rate_limited": False, "depth": 2, "source_type": "youtube_profile", "parent_url": "https://example.org/feature"},
            None,
            {"reasons": []},
        )

        self.assertEqual(influencer.name, "Coach Maya Official")
        self.assertEqual(influencer.handle, "coachmaya")
        self.assertEqual(influencer.followers, 44000)
        self.assertAlmostEqual(influencer.engagement_rate, 0.065)
        self.assertIn("https://example.org/feature", influencer.citations)
        self.assertIn("https://youtube.com/@coachmaya", influencer.citations)

    def test_engagement_sub_score_uses_real_sample_quality(self) -> None:
        by_identity = {}
        influencer = _get_or_create_influencer(
            by_identity,
            {
                "platform": "tiktok",
                "canonical_profile_url": "https://tiktok.com/@runwithjordan",
                "handle_or_username": "runwithjordan",
                "channel_id": None,
            },
        )
        influencer.name = "Jordan Chen"
        influencer.followers = 25000
        influencer.engagement_rate = 0.08
        influencer.source_payload["mentions"] = [
            {"context": "Jordan Chen is a helpful and authentic running creator.", "credentials": []}
        ]
        influencer.source_payload["engagement"] = {"sample_size": 10}

        scores = _build_sub_scores(influencer)
        self.assertGreaterEqual(scores["engagement"], 90)
        self.assertEqual(scores["data_source_count"], 1)


if __name__ == "__main__":
    unittest.main()
