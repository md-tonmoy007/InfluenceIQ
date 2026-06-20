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

from scraping_service.crawling.content_extractor import extract_role5_content
from scraping_service.crawling.fetcher import fetch_url
from scraping_service.crawling.search_providers import search_web


class DummyResponse:
    def __init__(self, text: str = "", json_payload: dict | None = None, status_code: int = 200) -> None:
        self.text = text
        self.content = text
        self.status_code = status_code
        self._json_payload = json_payload
        self.headers = {"content-type": "text/html"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self) -> dict:
        return self._json_payload or {}

try:
    from app.pipeline import _build_role5_candidate
except ModuleNotFoundError:
    _build_role5_candidate = None


class Role4ScrapingContractTest(unittest.TestCase):
    def test_extract_content_returns_role5_ready_payload(self) -> None:
        page = {
            "url": "https://source.example/nutrition-creators",
            "status": 200,
            "cached": False,
            "fetched_at": "2026-06-10T00:00:00+00:00",
            "provider": "fixture",
            "html": """
                <html>
                  <head>
                    <title>Top Nutrition Creators</title>
                    <meta name="description" content="Evidence-based creator profile">
                  </head>
                  <body>
                    <h1>Dr Sarah Tan</h1>
                    <p>Certified Nutritionist and MD. Verified. 124K followers.</p>
                    <p>Average likes: 5400. Comments: Helpful and authentic advice. Excellent explanation.</p>
                    <a href="https://instagram.com/drsarahtan">Instagram</a>
                    <a href="https://youtube.com/@drsarahtan">YouTube</a>
                  </body>
                </html>
            """,
        }

        content = extract_role5_content(page)

        self.assertEqual(content["title"], "Top Nutrition Creators")
        self.assertIn("https://instagram.com/drsarahtan", content["social_links"])
        self.assertIn("https://youtube.com/@drsarahtan", content["social_links"])
        self.assertEqual(content["metrics"]["followers"], 124000)
        self.assertEqual(content["metrics"]["average_engagement"], 5400)
        self.assertTrue(content["metrics"]["verified"])
        self.assertIn("role5_candidate", content)
        self.assertEqual(content["role5_candidate"]["followers"], 124000)
        self.assertGreaterEqual(len(content["role5_candidate"]["comments"]), 1)
        self.assertTrue(content["role5_candidate"]["source_evidence"]["profile_url_available"])

    def test_pipeline_candidate_merges_scraped_content_and_mentions(self) -> None:
        if _build_role5_candidate is None:
            self.skipTest("SQLAlchemy is not installed in the local test environment")

        content = extract_role5_content({
            "url": "https://source.example/profile",
            "status": 200,
            "html": "<p>Dr Sarah Tan @drsarahtan Certified Nutritionist. 124K followers.</p>",
        })
        mention = {
            "name": "Dr Sarah Tan",
            "handle": "@drsarahtan",
            "platforms": {"instagram": "https://instagram.com/drsarahtan"},
            "profile_urls": ["https://instagram.com/drsarahtan"],
            "credentials": ["Certified Nutritionist"],
            "professional_titles": ["nutritionist"],
            "source_url": "https://source.example/profile",
        }

        candidate = _build_role5_candidate(content, mention, {"risks": {"scam": False}})

        self.assertEqual(candidate["canonical_name"], "Dr Sarah Tan")
        self.assertEqual(candidate["followers"], 124000)
        self.assertEqual(candidate["platforms"]["instagram"], "https://instagram.com/drsarahtan")
        self.assertEqual(candidate["credentials"], ["Certified Nutritionist"])
        self.assertEqual(candidate["mentions"][0]["handle"], "@drsarahtan")
        self.assertEqual(candidate["data_source_count"], 1)

    def test_search_falls_back_to_real_discovery_targets_without_api_keys(self) -> None:
        with (
            patch("scraping_service.crawling.search_providers.settings.BRAVE_SEARCH_API_KEY", ""),
            patch("scraping_service.crawling.search_providers.settings.OPENSERP_URL", ""),
        ):
            results = search_web("nutrition creators", limit=3)

        self.assertEqual(len(results), 3)
        self.assertTrue(all("example.com" not in result["url"] for result in results))
        self.assertTrue(any("youtube.com" in result["url"] for result in results))

    def test_fetch_url_routes_youtube_profile_to_platform_provider(self) -> None:
        html = """
            <html><head>
              <meta property="og:title" content="Trail Coach - YouTube">
              <meta name="description" content="124K subscribers. Certified trail running coach.">
              <meta itemprop="channelId" content="UC123">
            </head><body>Verified</body></html>
        """
        rss = """<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom"
                  xmlns:yt="http://www.youtube.com/xml/schemas/2015"
                  xmlns:media="http://search.yahoo.com/mrss/">
              <entry><yt:videoId>v1</yt:videoId><title>Trail gear review</title>
              <published>2026-01-01T00:00:00+00:00</published>
              <media:group><media:description>Helpful authentic comments</media:description></media:group></entry>
            </feed>
        """

        def fake_get(url: str, *args, **kwargs):
            if "feeds/videos.xml" in url:
                return DummyResponse(rss)
            return DummyResponse(html)

        with (
            patch("scraping_service.crawling.fetcher.get_cached_page", return_value=None),
            patch("scraping_service.crawling.fetcher.store_cached_page"),
            patch("scraping_service.crawling.providers.youtube.httpx.get", side_effect=fake_get),
        ):
            page = fetch_url("https://www.youtube.com/@trailcoach")

        content = extract_role5_content(page)
        self.assertEqual(page["provider"], "youtube")
        self.assertIn("Trail Coach", content["title"])
        self.assertEqual(content["role5_candidate"]["followers"], 124000)
        self.assertIn("https://youtube.com/@trailcoach", content["role5_candidate"]["profile_urls"])

    def test_fetch_url_routes_instagram_profile_to_platform_provider(self) -> None:
        payload = {
            "data": {
                "user": {
                    "username": "drsarahtan",
                    "full_name": "Dr Sarah Tan",
                    "biography": "Certified Nutritionist and MD",
                    "is_verified": True,
                    "edge_followed_by": {"count": 124000},
                    "edge_follow": {"count": 900},
                    "edge_owner_to_timeline_media": {
                        "edges": [{
                            "node": {
                                "id": "1",
                                "shortcode": "abc",
                                "edge_liked_by": {"count": 5400},
                                "edge_media_to_comment": {"count": 120},
                                "edge_media_to_caption": {"edges": [{"node": {"text": "Evidence based advice"}}]},
                            }
                        }]
                    },
                    "edge_felix_video_timeline": {"edges": []},
                    "bio_links": [{"url": "https://drsarah.example"}],
                }
            }
        }
        with (
            patch("scraping_service.crawling.fetcher.get_cached_page", return_value=None),
            patch("scraping_service.crawling.fetcher.store_cached_page"),
            patch("scraping_service.crawling.providers.instagram.httpx.get", return_value=DummyResponse(json_payload=payload)),
        ):
            page = fetch_url("https://instagram.com/drsarahtan")

        content = extract_role5_content(page)
        self.assertEqual(page["provider"], "instagram_web_profile")
        self.assertEqual(content["role5_candidate"]["followers"], 124000)
        self.assertEqual(content["role5_candidate"]["average_engagement"], 5400)
        self.assertTrue(content["role5_candidate"]["verified"])

    def test_fetch_url_routes_tiktok_and_x_profiles_to_platform_providers(self) -> None:
        tiktok_html = """
            <html><head><meta property="og:title" content="Maya Trails | TikTok">
            <meta name="description" content="Outdoor creator with 88K Followers and 1.2M Likes"></head>
            <body>Verified</body></html>
        """
        x_html = """
            <html><head><meta property="og:title" content="Maya Trails on X">
            <meta name="description" content="Outdoor creator and gear reviewer"></head>
            <body>88K Followers 300 Following Verified account</body></html>
        """

        with (
            patch("scraping_service.crawling.fetcher.get_cached_page", return_value=None),
            patch("scraping_service.crawling.fetcher.store_cached_page"),
            patch("scraping_service.crawling.providers.tiktok.httpx.get", return_value=DummyResponse(tiktok_html)),
        ):
            tiktok_page = fetch_url("https://www.tiktok.com/@mayatrails")
        with (
            patch("scraping_service.crawling.fetcher.get_cached_page", return_value=None),
            patch("scraping_service.crawling.fetcher.store_cached_page"),
            patch("scraping_service.crawling.providers.x.httpx.get", return_value=DummyResponse(x_html)),
        ):
            x_page = fetch_url("https://twitter.com/mayatrails")

        tiktok_content = extract_role5_content(tiktok_page)
        x_content = extract_role5_content(x_page)
        self.assertEqual(tiktok_page["provider"], "tiktok_meta")
        self.assertEqual(x_page["provider"], "x_meta")
        self.assertEqual(tiktok_content["role5_candidate"]["followers"], 88000)
        self.assertEqual(x_content["role5_candidate"]["followers"], 88000)


if __name__ == "__main__":
    unittest.main()
