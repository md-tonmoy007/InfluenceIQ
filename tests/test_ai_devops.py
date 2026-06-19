from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from app.scoring.formula import calculate_final_score, confidence_for_sources, grade_for_score
from app.scoring.normalize import normalize_score
from app.service_roles import TASK_QUEUE_BY_NAME, WORKER_QUEUES
from app.services import pipeline_state
from app.services.platform_enrichment import enrich_tiktok_profile, enrich_youtube_profile, normalize_platform_identity
from app.tasks.crawl import extract_content, fetch_page
from app.tasks.extract import resolve_identity_llm
from app.tasks.score import classify_brand_safety, score_influencer
from app.tasks.search import execute_search, generate_queries
from app.llm.client import LLMResponse


class FakePipeline:
    def __init__(self) -> None:
        self.commands: list[tuple] = []

    def rpush(self, *args) -> "FakePipeline":
        self.commands.append(("rpush", *args))
        return self

    def expire(self, *args) -> "FakePipeline":
        self.commands.append(("expire", *args))
        return self

    def publish(self, *args) -> "FakePipeline":
        self.commands.append(("publish", *args))
        return self

    def hset(self, *args, **kwargs) -> "FakePipeline":
        self.commands.append(("hset", args, kwargs))
        return self

    def execute(self) -> list:
        return []


class FakeRedis:
    def __init__(self) -> None:
        self.pipeline_instance = FakePipeline()
        self.sequence = 0
        self.hashes: dict[str, dict[str, str]] = {}
        self.lists: dict[str, list[str]] = {}

    def incr(self, key: str) -> int:
        self.sequence += 1
        return self.sequence

    def pipeline(self) -> FakePipeline:
        return self.pipeline_instance

    def hgetall(self, key: str) -> dict[str, str]:
        return self.hashes.get(key, {})

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]


class FakeCacheRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value

    def set(self, key: str, value: str) -> None:
        self.values[key] = value


class AiDevOpsTest(unittest.TestCase):
    def test_task_routes_use_four_expected_queues(self) -> None:
        self.assertEqual(
            TASK_QUEUE_BY_NAME,
            {
                "app.tasks.search.generate_queries": "search_queue",
                "app.tasks.search.execute_search": "search_queue",
                "app.tasks.crawl.fetch_page": "crawl_queue",
                "app.tasks.crawl.extract_content": "crawl_queue",
                "app.tasks.extract.extract_influencers": "extract_queue",
                "app.tasks.extract.resolve_identity_llm": "extract_queue",
                "app.tasks.score.classify_brand_safety": "score_queue",
                "app.tasks.score.score_influencer": "score_queue",
            },
        )
        self.assertEqual(WORKER_QUEUES, ["crawl_queue", "extract_queue", "score_queue", "search_queue"])

    def test_emit_event_writes_list_ttl_and_pubsub(self) -> None:
        fake = FakeRedis()
        pipeline_state._state_redis.cache_clear()

        with patch("app.services.pipeline_state.redis.from_url", return_value=fake):
            event = pipeline_state.emit_event("campaign-1", "query.generated", {"queries": ["x"]})

        self.assertEqual(event["event_id"], 1)
        self.assertEqual(event["type"], "query.generated")
        commands = fake.pipeline_instance.commands
        self.assertEqual(commands[0][0], "rpush")
        self.assertEqual(commands[0][1], "pipeline_events:campaign-1")
        self.assertEqual(json.loads(commands[0][2])["payload"], {"queries": ["x"]})
        self.assertIn(("expire", "pipeline_events:campaign-1", 3600), commands)
        self.assertEqual(commands[-1][0], "publish")
        self.assertEqual(commands[-1][1], "campaign:campaign-1")

    def test_update_state_writes_hash_and_ttl(self) -> None:
        fake = FakeRedis()
        pipeline_state._state_redis.cache_clear()

        with patch("app.services.pipeline_state.redis.from_url", return_value=fake):
            encoded = pipeline_state.update_state("campaign-1", phase="score", done=True, count=3)

        self.assertEqual(encoded, {"phase": "score", "done": "true", "count": "3"})
        commands = fake.pipeline_instance.commands
        self.assertEqual(commands[0][0], "hset")
        self.assertEqual(commands[0][1][0], "pipeline_state:campaign-1")
        self.assertEqual(commands[0][2]["mapping"], encoded)
        self.assertIn(("expire", "pipeline_state:campaign-1", 7200), commands)

    def test_scoring_normalization_formula_and_confidence_cap(self) -> None:
        self.assertEqual(normalize_score(-5), 0.0)
        self.assertEqual(normalize_score(150), 100.0)
        self.assertEqual(grade_for_score(87), "B")

        score, normalized = calculate_final_score(
            {
                "relevance": 100,
                "credibility": 80,
                "engagement": 60,
                "sentiment": 70,
                "brand_safety": 90,
            }
        )
        self.assertEqual(normalized["relevance"], 100.0)
        self.assertEqual(score, 82.5)
        self.assertEqual(confidence_for_sources(1, 95), ("Low", 70.0))

    def test_brand_safety_and_score_tasks_have_stable_fallbacks(self) -> None:
        with patch("app.tasks.score.update_state"):
            result = classify_brand_safety.run(
                "campaign-1",
                {"url": "https://example.com", "content": "This contains a guaranteed profit scam."},
            )
        self.assertTrue(result["risks"]["scam"])
        self.assertEqual(result["source_url"], "https://example.com")

        with (
            patch("app.tasks.score.emit_event"),
            patch("app.tasks.score.update_state"),
        ):
            score = score_influencer.run(
                "campaign-1",
                "influencer-1",
                {
                    "relevance": 90,
                    "credibility": 80,
                    "engagement": 70,
                    "sentiment": 75,
                    "brand_safety": 95,
                    "data_source_count": 4,
                },
            )

        self.assertEqual(score["influencer_id"], "influencer-1")
        self.assertEqual(score["grade"], "B")
        self.assertEqual(score["confidence"], "Medium")
        self.assertEqual(score["data_source_count"], 4)

    def test_generate_queries_uses_llm_response(self) -> None:
        llm_response = LLMResponse(
            text='{"queries":["wellness creators instagram","registered dietitian youtube"]}',
            provider="openrouter",
            model="qwen/qwen3-coder:free",
            fallback=False,
        )
        with (
            patch("app.tasks.search._campaign_context", return_value={"brand": "Acme", "product": "Greens", "goal": "Find creators"}),
            patch("app.tasks.search.complete_or_fallback", return_value=llm_response),
            patch("app.tasks.search.update_state"),
            patch("app.tasks.search.emit_event"),
        ):
            queries = generate_queries.run("campaign-1")

        self.assertEqual(queries, ["wellness creators instagram", "registered dietitian youtube"])

    def test_execute_search_uses_live_results_when_available(self) -> None:
        results = [{"url": "https://example.org/creator", "title": "Creator", "snippet": "Snippet", "relevance_score": 72}]
        with (
            patch("app.tasks.search.settings.SERP_API_KEY", "token"),
            patch("app.tasks.search.settings.BRAVE_SEARCH_API_KEY", ""),
            patch("app.tasks.search.settings.SCRAPE_DO_API_KEY", ""),
            patch("app.tasks.search._search_via_serp_api", return_value=results),
            patch("app.tasks.search.update_state"),
            patch("app.tasks.search.emit_event"),
        ):
            found = execute_search.run("campaign-1", "wellness creators")

        self.assertEqual(found, results)

    def test_fetch_page_uses_cache_before_refetch(self) -> None:
        fake_cache = FakeCacheRedis()
        html = "<html><head><title>Live Page</title><meta name=\"author\" content=\"Jane\" /></head><body><a href=\"https://instagram.com/jane\">Profile</a></body></html>"
        with (
            patch("app.tasks.crawl._cache_redis", return_value=fake_cache),
            patch("app.tasks.crawl.settings.SCRAPE_DO_API_KEY", "token"),
            patch("app.tasks.crawl._fetch_via_scrape_do", return_value=html) as fetch_mock,
            patch("app.tasks.crawl.update_state"),
            patch("app.tasks.crawl.emit_event"),
        ):
            first = fetch_page.run("campaign-1", "https://example.org/profile")
            second = fetch_page.run("campaign-1", "https://example.org/profile")

        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(fetch_mock.call_count, 1)

        extracted = extract_content.run(second)
        self.assertEqual(extracted["title"], "Live Page")
        self.assertIn("https://instagram.com/jane", extracted["social_links"])
        self.assertEqual(extracted["metadata"]["author"], "Jane")

    def test_fetch_page_social_rate_limit_emits_event_and_waits(self) -> None:
        fake_cache = FakeCacheRedis()
        fake_cache.values["rate_limit:tiktok.com"] = "100"
        with (
            patch("app.tasks.crawl._cache_redis", return_value=fake_cache),
            patch("app.tasks.crawl.settings.SCRAPE_DO_API_KEY", "token"),
            patch("app.tasks.crawl._utc_timestamp", return_value=101.0),
            patch("app.tasks.crawl._sleep") as sleep_mock,
            patch("app.tasks.crawl._fetch_via_scrape_do", return_value={"html": "<html>ok</html>", "status": 200}),
            patch("app.tasks.crawl.update_state"),
            patch("app.tasks.crawl.emit_event") as emit_mock,
        ):
            page = fetch_page.run("campaign-1", "https://tiktok.com/@runner")

        self.assertTrue(page["rate_limited"])
        sleep_mock.assert_called()
        emitted = [call.args[1] for call in emit_mock.call_args_list]
        self.assertIn("page.rate_limited", emitted)

    def test_fetch_page_retries_on_bot_block_marker(self) -> None:
        fake_cache = FakeCacheRedis()
        with (
            patch("app.tasks.crawl._cache_redis", return_value=fake_cache),
            patch("app.tasks.crawl.settings.SCRAPE_DO_API_KEY", "token"),
            patch("app.tasks.crawl._sleep"),
            patch(
                "app.tasks.crawl._fetch_via_scrape_do",
                side_effect=[
                    {"html": "<html>captcha</html>", "status": 200},
                    {"html": "<html>ok</html>", "status": 200},
                ],
            ),
            patch("app.tasks.crawl.update_state"),
            patch("app.tasks.crawl.emit_event") as emit_mock,
        ):
            page = fetch_page.run("campaign-1", "https://example.org/profile")

        self.assertEqual(page["attempt_count"], 2)
        emitted = [call.args[1] for call in emit_mock.call_args_list]
        self.assertIn("page.retry_scheduled", emitted)

    def test_fetch_page_uses_archive_fallback_after_retry_exhaustion(self) -> None:
        fake_cache = FakeCacheRedis()
        with (
            patch("app.tasks.crawl._cache_redis", return_value=fake_cache),
            patch("app.tasks.crawl.settings.SCRAPE_DO_API_KEY", "token"),
            patch("app.tasks.crawl._sleep"),
            patch(
                "app.tasks.crawl._fetch_via_scrape_do",
                side_effect=[
                    {"html": "", "status": 429},
                    {"html": "", "status": 429},
                    {"html": "", "status": 429},
                    {"html": "<html>archived</html>", "status": 200},
                ],
            ) as fetch_mock,
            patch("app.tasks.crawl.update_state"),
            patch("app.tasks.crawl.emit_event") as emit_mock,
        ):
            page = fetch_page.run("campaign-1", "https://example.org/profile")

        self.assertTrue(page["archive_fallback_used"])
        self.assertEqual(page["attempt_count"], 4)
        self.assertIn("web.archive.org", fetch_mock.call_args_list[-1].args[0])
        emitted = [call.args[1] for call in emit_mock.call_args_list]
        self.assertIn("page.archive_fallback", emitted)

    def test_extract_content_selects_recursive_profile_links(self) -> None:
        page = {
            "url": "https://example.org/creators",
            "html": (
                "<html><body>"
                "<a href=\"/about\">About</a>"
                "<a href=\"https://youtube.com/@coachmaya\">YouTube</a>"
                "<a href=\"https://tiktok.com/@coachmaya\">TikTok</a>"
                "<a href=\"/tag/training\">Tag</a>"
                "</body></html>"
            ),
            "depth": 1,
        }
        extracted = extract_content.run(page)
        self.assertIn("https://example.org/about", extracted["discovered_links"])
        self.assertIn("https://youtube.com/@coachmaya", extracted["discovered_links"])
        self.assertIn("https://tiktok.com/@coachmaya", extracted["discovered_links"])
        self.assertNotIn("https://example.org/tag/training", extracted["discovered_links"])

    def test_youtube_identity_and_enrichment(self) -> None:
        identity = normalize_platform_identity("https://www.youtube.com/@TrailCoach")
        self.assertEqual(identity["canonical_profile_url"], "https://youtube.com/@TrailCoach")
        with (
            patch("app.services.platform_enrichment.settings.YOUTUBE_API_KEY", "token"),
            patch(
                "app.services.platform_enrichment._youtube_api_get",
                side_effect=[
                    {
                        "items": [
                            {
                                "id": "UC123",
                                "snippet": {"title": "Trail Coach", "description": "Outdoor coach", "customUrl": "@TrailCoach"},
                                "statistics": {"subscriberCount": "12000", "videoCount": "44", "viewCount": "900000"},
                            }
                        ]
                    },
                    {"items": [{"id": {"videoId": "v1"}}, {"id": {"videoId": "v2"}}]},
                    {
                        "items": [
                            {"id": "v1", "statistics": {"viewCount": "1000", "likeCount": "80", "commentCount": "20"}},
                            {"id": "v2", "statistics": {"viewCount": "500", "likeCount": "25", "commentCount": "5"}},
                        ]
                    },
                ],
            ),
        ):
            enriched = enrich_youtube_profile(identity)

        self.assertEqual(enriched["followers"], 12000)
        self.assertAlmostEqual(enriched["engagement_rate"], 0.08, places=3)
        self.assertEqual(enriched["source_payload"]["engagement"]["sample_size"], 2)

    def test_tiktok_identity_and_enrichment(self) -> None:
        identity = normalize_platform_identity("https://www.tiktok.com/@runwithjordan?lang=en")
        self.assertEqual(identity["canonical_profile_url"], "https://tiktok.com/@runwithjordan")
        html = """
        <html><body><script id="SIGI_STATE" type="application/json">
        {"UserModule":{"users":{"runwithjordan":{"uniqueId":"runwithjordan","nickname":"Jordan Chen","signature":"Trail runner","verified":true,"stats":{"followerCount":25000,"followingCount":120,"heartCount":400000}}}},
         "ItemModule":{"p1":{"id":"p1","stats":{"playCount":1000,"diggCount":100,"commentCount":20,"shareCount":10}},
                       "p2":{"id":"p2","stats":{"playCount":500,"diggCount":40,"commentCount":5,"shareCount":5}}}}
        </script></body></html>
        """
        enriched = enrich_tiktok_profile(identity, html)
        self.assertEqual(enriched["followers"], 25000)
        self.assertTrue(enriched["source_payload"]["verified"])
        self.assertEqual(enriched["source_payload"]["engagement"]["sample_size"], 2)

    def test_identity_resolution_fallback(self) -> None:
        result = resolve_identity_llm.run(
            {"name": "Dr Sarah Tan", "platforms": {"instagram": "@drsarahtan"}},
            {"name": "Sarah Tan MD", "platforms": {"instagram": "@drsarahtan"}},
        )

        self.assertTrue(result["merge"])
        self.assertGreaterEqual(result["confidence"], 0.9)


if __name__ == "__main__":
    unittest.main()
