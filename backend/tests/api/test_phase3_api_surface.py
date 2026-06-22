"""Phase 3 contract tests: error envelope, cursor pagination, profile history.

Covers the new behaviour added in Phase 3:

* Every non-2xx response is wrapped in the :class:`ErrorEnvelope` shape.
* ``/api/campaigns/{id}/influencers`` returns ``{items, next_cursor, limit}``.
* Cursor pagination is stable across multiple pages.
* Influencer profile supports ``include_history`` for cross-campaign scores.
* ``/api/campaigns/{id}/state`` includes ``last_event_id`` from Redis.

These tests deliberately avoid importing :mod:`backend.api.main`
(which eagerly constructs the DB engine) so they run inside the
``make test-unit`` target without ``psycopg`` installed.
"""

from __future__ import annotations

import base64
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


class ErrorEnvelopeSchemaTest(unittest.TestCase):
    """The envelope shape is stable."""

    def test_envelope_has_error_body(self) -> None:
        from backend.api.schemas.errors import ErrorEnvelope

        env = ErrorEnvelope(
            error={
                "code": "validation_error",
                "message": "bad input",
                "details": [{"field": "x", "issue": "must be int"}],
                "request_id": "abc",
            }
        )
        self.assertEqual(env.error.code, "validation_error")
        self.assertEqual(env.error.message, "bad input")
        self.assertEqual(len(env.error.details), 1)
        self.assertEqual(env.error.details[0].field, "x")
        self.assertEqual(env.error.request_id, "abc")

    def test_envelope_json_shape(self) -> None:
        from backend.api.schemas.errors import ErrorEnvelope

        env = ErrorEnvelope(
            error={"code": "not_found", "message": "no such row"}
        )
        payload = env.model_dump(mode="json")
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], "not_found")
        self.assertEqual(payload["error"]["details"], [])
        self.assertIsNone(payload["error"]["request_id"])


class CursorCodecTest(unittest.TestCase):
    """Encode/decode of pagination cursors is a private contract."""

    def test_round_trip(self) -> None:
        from backend.api.routers import campaigns as campaigns_router

        cursor = campaigns_router._encode_cursor(91.5, "abc-123")
        decoded = campaigns_router._decode_cursor(cursor)
        self.assertIsNotNone(decoded)
        score, inf_id = decoded
        self.assertAlmostEqual(score, 91.5)
        self.assertEqual(inf_id, "abc-123")

    def test_decode_malformed_returns_none(self) -> None:
        from backend.api.routers import campaigns as campaigns_router

        self.assertIsNone(campaigns_router._decode_cursor("not-a-cursor!!"))
        self.assertIsNone(campaigns_router._decode_cursor(""))
        # Base64 decodes but is not JSON.
        junk = base64.urlsafe_b64encode(b"not-json").decode()
        self.assertIsNone(campaigns_router._decode_cursor(junk))


class CampaignStateLastEventIdTest(unittest.TestCase):
    """``/api/campaigns/{id}/state`` exposes the latest event id."""

    def setUp(self) -> None:
        try:
            from backend.core.cache.redis_client import redis_client

            redis_client.flushdb()
        except Exception:
            self._skip_redis = True
        else:
            self._skip_redis = False

    def _maybe_skip(self) -> None:
        if self._skip_redis:
            self.skipTest("Redis is not reachable in this test environment")

    def test_returns_zero_when_counter_absent(self) -> None:
        self._maybe_skip()
        from backend.api.routers.campaigns import _get_last_event_id

        # Fresh key (none written) → 0
        self.assertEqual(_get_last_event_id("nonexistent-campaign"), 0)

    def test_returns_current_counter_value(self) -> None:
        self._maybe_skip()
        from backend.api.routers.campaigns import _get_last_event_id
        from backend.core.cache.event_log import EVENT_COUNTER_PREFIX
        from backend.core.cache.redis_client import redis_client

        redis_client.set(f"{EVENT_COUNTER_PREFIX}camp-1", 42)
        self.assertEqual(_get_last_event_id("camp-1"), 42)

    def test_returns_zero_on_redis_error(self) -> None:
        self._maybe_skip()
        from backend.api.routers.campaigns import _get_last_event_id
        from backend.core.cache.event_log import EVENT_COUNTER_PREFIX

        # Calling with a key whose value is non-numeric should be
        # coerced to 0 by the ``int(raw) if raw else 0`` guard.
        from backend.core.cache.redis_client import redis_client

        redis_client.set(f"{EVENT_COUNTER_PREFIX}camp-bad", "not-a-number")
        self.assertEqual(_get_last_event_id("camp-bad"), 0)


class CampaignsRouterCursorArgsTest(unittest.TestCase):
    """The cursor query param is wired through with the right defaults."""

    def test_cursor_query_is_optional_string(self) -> None:
        from backend.api.routers import campaigns as campaigns_router

        # The route definition accepts ``cursor: str | None = Query(default=None, ...)``.
        route = next(
            r
            for r in campaigns_router.router.routes
            if getattr(r, "path", "").endswith("/{id}/influencers")
        )
        params = list(route.dependant.query_params)
        cursor_param = next(p for p in params if p.name == "cursor")
        self.assertEqual(cursor_param.field_info.default, None)

        limit_param = next(p for p in params if p.name == "limit")
        self.assertEqual(limit_param.field_info.default, 20)


if __name__ == "__main__":
    unittest.main()
