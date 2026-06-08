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
from app.llm.client import available_provider_for
from app.tasks.extract import resolve_identity_llm
from app.tasks.score import classify_brand_safety, score_influencer


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

    def incr(self, key: str) -> int:
        self.sequence += 1
        return self.sequence

    def pipeline(self) -> FakePipeline:
        return self.pipeline_instance


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

    def test_identity_resolution_fallback(self) -> None:
        result = resolve_identity_llm.run(
            {"name": "Dr Sarah Tan", "platforms": {"instagram": "@drsarahtan"}},
            {"name": "Sarah Tan MD", "platforms": {"instagram": "@drsarahtan"}},
        )

        self.assertTrue(result["merge"])
        self.assertGreaterEqual(result["confidence"], 0.9)

    def test_llm_provider_selection_uses_task_specific_provider_and_model(self) -> None:
        with (
            patch("app.llm.client.settings.OPENROUTER_API_KEY", "router-key"),
            patch("app.llm.client.settings.GEMINI_API_KEY", "gemini-key"),
            patch("app.llm.client.settings.GENERATE_QUERY_AI_PROVIDER", "openrouter"),
            patch("app.llm.client.settings.GENERATE_QUERY_AI_MODEL", "openai/gpt-4o-mini"),
            patch("app.llm.client.settings.CLASSIFY_BRAND_SAFETY_AI_PROVIDER", "gemini"),
            patch("app.llm.client.settings.CLASSIFY_BRAND_SAFETY_AI_MODEL", "gemini-2.5-flash"),
            patch("app.llm.client.settings.RESOLVE_IDENTITY_AI_PROVIDER", "openrouter"),
            patch("app.llm.client.settings.RESOLVE_IDENTITY_AI_MODEL", "anthropic/claude-3.5-haiku"),
        ):
            self.assertEqual(
                available_provider_for("generate_queries"),
                ("openrouter", "openai/gpt-4o-mini"),
            )
            self.assertEqual(
                available_provider_for("classify_brand_safety"),
                ("gemini", "gemini-2.5-flash"),
            )
            self.assertEqual(
                available_provider_for("resolve_identity_llm"),
                ("openrouter", "anthropic/claude-3.5-haiku"),
            )


if __name__ == "__main__":
    unittest.main()
