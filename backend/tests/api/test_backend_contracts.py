from __future__ import annotations

import asyncio
import os
import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.routers import campaigns as campaigns_router
from backend.api.routers import websocket as websocket_router
from backend.core.database import models
from backend.core.database.session import get_db


class FakeQuery:
    def __init__(self, session: FakeSession, entities: tuple):
        self.session = session
        self.entities = entities

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        results = self._results()
        return results[0] if results else None

    def all(self):
        return list(self._results())

    def limit(self, _n):
        return self

    def offset(self, _n):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._results())

    def distinct(self):
        return self

    def delete(self):
        return 0

    def _results(self):
        if self.entities == (models.Campaign,):
            return [self.session.campaign] if self.session.campaign else []
        if self.entities == (models.Influencer,):
            return [self.session.influencer] if self.session.influencer else []
        if self.entities == (models.InfluencerScore,):
            return [self.session.score] if self.session.score else []
        if self.entities == (models.InfluencerScore, models.Influencer):
            if self.session.score and self.session.influencer:
                return [(self.session.score, self.session.influencer)]
            return []
        if self.entities == (models.CrawlSourceInfluencer, models.CrawlSource):
            if self.session.link and self.session.source:
                return [(self.session.link, self.session.source)]
            return []
        if self.entities == (models.CrawlSource,):
            return [self.session.source] if self.session.source else []
        return []


class FakeSession:
    def __init__(self):
        self.campaign = None
        self.influencer = None
        self.score = None
        self.source = None
        self.link = None
        self.added = []
        self.committed = False

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)
        if isinstance(obj, models.Campaign):
            self.campaign = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    def query(self, *entities):
        return FakeQuery(self, entities)

    def close(self):
        return None


class FakePubSub:
    def __init__(self, live_event: dict):
        self.live_event = live_event
        self.sent = False

    async def subscribe(self, _channel):
        return None

    async def unsubscribe(self, _channel):
        return None

    async def close(self):
        return None

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        await asyncio.sleep(0)
        if not self.sent:
            self.sent = True
            return {"type": "message", "data": __import__("json").dumps(self.live_event)}
        await asyncio.sleep(0.01)
        return None


class FakeRedisConn:
    def __init__(self, live_event: dict | None = None):
        self._live_event = live_event

    async def close(self):
        return None

    def pubsub(self):
        return FakePubSub(self._live_event or {})


class BackendContractsTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides.clear()
        self.session = FakeSession()

        def _override_get_db():
            yield self.session

        app.dependency_overrides[get_db] = _override_get_db

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_create_campaign_initializes_state_and_starts_pipeline(self):
        payload = {
            "product": "Protein Powder",
            "industry": "fitness",
            "goals": "awareness",
            "target_audience": "athletes",
            "preferred_platforms": ["youtube"],
            "budget_range": "$1000-$2000",
        }
        with (
            patch.object(campaigns_router, "initialize_pipeline_state") as init_state,
            patch.object(campaigns_router, "get_pipeline_state", return_value={"phase": "initializing"}),
            patch("backend.pipeline.tasks.start_campaign", return_value={"started": True}) as start_campaign,
        ):
            response = self.client.post("/api/campaigns", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["pipeline_state"]["phase"], "initializing")
        self.assertEqual(self.session.campaign.product, "Protein Powder")
        self.assertEqual(self.session.campaign.status, "running")
        self.assertIsNotNone(self.session.campaign.started_at)
        init_state.assert_called_once()
        start_campaign.assert_called_once()

    def test_campaign_state_falls_back_to_durable_status(self):
        campaign_id = uuid.uuid4()
        self.session.campaign = models.Campaign(
            id=campaign_id,
            product="Product",
            niche="wellness",
            status="completed",
            started_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            completed_at=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
        )
        with patch.object(campaigns_router, "get_pipeline_state", return_value=None):
            response = self.client.get(f"/api/campaigns/{campaign_id}/state")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["phase"], "completed")
        self.assertIn("durable campaign lifecycle", body["message"])

    def test_campaign_influencers_includes_provenance_and_explanations(self):
        campaign_id = uuid.uuid4()
        influencer_id = uuid.uuid4()
        self.session.campaign = models.Campaign(id=campaign_id, product="Product", niche="wellness", status="partial")
        self.session.influencer = models.Influencer(
            id=influencer_id,
            canonical_name="Dr Test",
            platforms={"youtube": "youtube.com/@drtest"},
            credentials=["MD"],
            mentions=[{"name": "Dr Test", "source_url": "https://example.com/source"}],
        )
        self.session.score = models.InfluencerScore(
            id=uuid.uuid4(),
            influencer_id=influencer_id,
            campaign_id=campaign_id,
            final_score=91.0,
            relevance_score=90.0,
            credibility_score=94.0,
            engagement_score=88.0,
            sentiment_score=87.0,
            brand_safety_score=96.0,
            confidence_level="High",
            data_source_count=2,
            score_version="v2",
            signal_scores={"graph": 0.84},
            risk_category="low",
            detection_category="trusted",
            positive_reasons=["licensed clinician"],
            negative_reasons=["limited source diversity"],
            computed_at=datetime.now(UTC),
        )
        self.session.source = models.CrawlSource(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            influencer_id=influencer_id,
            url="https://example.com/source",
            title="Evidence-based review",
            relevance_score=91.2,
            status="extracted",
            content="source content",
        )
        self.session.link = models.CrawlSourceInfluencer(
            id=uuid.uuid4(),
            crawl_source_id=self.session.source.id,
            influencer_id=influencer_id,
            mention_id="m-1",
            mention={"name": "Dr Test", "context": "quoted"},
        )

        response = self.client.get(f"/api/campaigns/{campaign_id}/influencers")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        # Phase 3: response is now {items, next_cursor, limit}; check items.
        self.assertEqual(len(body["items"]), 1)
        self.assertIsNone(body["next_cursor"])
        row = body["items"][0]
        self.assertEqual(row["risk_category"], "low")
        self.assertEqual(row["detection_category"], "trusted")
        self.assertEqual(row["positive_reasons"], ["licensed clinician"])
        self.assertEqual(row["sources"][0]["mention_id"], "m-1")
        self.assertEqual(row["sources"][0]["url"], "https://example.com/source")

    def test_websocket_replays_and_streams_live_events(self):
        campaign_id = uuid.uuid4()
        replay_event = {
            "event_id": 2,
            "type": "query.generated",
            "campaign_id": str(campaign_id),
            "timestamp": "2026-06-21T10:00:00Z",
            "payload": {"query": "alpha"},
        }
        live_event = {
            "event_id": 3,
            "type": "score.calculated",
            "campaign_id": str(campaign_id),
            "timestamp": "2026-06-21T10:00:01Z",
            "payload": {"final_score": 91},
        }
        redis_conns = [FakeRedisConn(), FakeRedisConn(live_event)]

        def _from_url(*args, **kwargs):
            return redis_conns.pop(0)

        with (
            patch.object(websocket_router, "aget_event_replay", return_value=[replay_event]),
            patch.object(websocket_router.aioredis, "from_url", side_effect=_from_url),
        ):
            with self.client.websocket_connect(f"/ws/campaign/{campaign_id}?last_event_id=1") as ws:
                first = ws.receive_json()
                second = ws.receive_json()

        self.assertEqual(first["event_id"], 2)
        self.assertEqual(first["type"], "query.generated")
        self.assertEqual(second["event_id"], 3)
        self.assertEqual(second["type"], "score.calculated")


if __name__ == "__main__":
    unittest.main()
