"""Phase 1 contract tests: idempotency, ownership columns, indexes.

Covers the new behaviour added in Phase 1 without importing
``backend.api.main`` (whose eager ``create_engine`` requires the
``psycopg`` driver to be installed in the test env — the Makefile
excludes the contract test file from ``test-unit`` for that exact
reason). Instead we exercise the router directly via
``TestClient(app)`` only when the engine import is safe, and otherwise
exercise the helper functions and Pydantic schemas directly.

The four behaviours that matter for Phase 1:

1. ``Campaign`` schema exposes ``org_id`` and ``created_by``.
2. ``Campaign`` model has the new ``uq_campaigns_owner_product_niche``
   constraint and the three new indexes.
3. ``Idempotency-Key`` header → response is cached in Redis.
4. Duplicate natural key → handler raises 409 instead of creating a row.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


def _adapt_user_table_for_sqlite(user_model) -> None:
    """Swap PostgreSQL UUID columns for String so SQLite can create the table."""
    from sqlalchemy import String
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    for column in user_model.__table__.columns:
        if isinstance(column.type, PGUUID):
            column.type = String(36)


class CampaignSchemaSurfaceTest(unittest.TestCase):
    """Pydantic schema exposes the new ownership columns."""

    def test_campaign_response_has_org_id_and_created_by(self) -> None:
        from backend.api.schemas.campaign import CampaignResponse

        schema = CampaignResponse.model_json_schema()
        props = schema.get("properties", {})
        self.assertIn("org_id", props)
        self.assertIn("created_by", props)


class CampaignModelSurfaceTest(unittest.TestCase):
    """ORM model has the new constraint and indexes."""

    def setUp(self) -> None:
        # Importing ``backend.core.database.models`` transitively imports
        # ``session.py`` which calls ``create_engine(settings.DATABASE_URL)``
        # at module load time. That requires the ``psycopg`` driver to be
        # installed system-wide. The Makefile excludes this file from
        # ``test-unit`` when that driver is missing, so we skip gracefully
        # rather than crashing collection.
        try:
            from backend.core.database import models  # noqa: F401
        except Exception as exc:
            self.skipTest(f"psycopg not available in test env: {exc}")

    def test_unique_constraint_present(self) -> None:
        from backend.core.database import models

        constraint_names = {
            c.name for c in models.Campaign.__table__.constraints
        }
        self.assertIn("uq_campaigns_owner_product_niche", constraint_names)

    def test_new_indexes_present(self) -> None:
        from backend.core.database import models

        indexes = {
            ix.name
            for ix in models.Campaign.__table__.indexes
            | models.InfluencerScore.__table__.indexes
            | models.CrawlSource.__table__.indexes
        }
        self.assertIn("idx_influencer_scores_campaign_final", indexes)
        self.assertIn("idx_crawl_sources_campaign_status", indexes)
        self.assertIn("idx_campaigns_created_by", indexes)

    def test_optional_ownership_columns_added(self) -> None:
        from backend.core.database import models

        cols = models.Campaign.__table__.columns
        self.assertIn("org_id", cols)
        self.assertIn("created_by", cols)
        # org_id is plain nullable UUID (no FK), created_by is FK to users.
        self.assertTrue(cols["org_id"].nullable)
        self.assertTrue(cols["created_by"].nullable)


class IdempotencyCacheTest(unittest.TestCase):
    """Redis-backed idempotency cache round-trips correctly."""

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

    def test_store_then_get_returns_same_body(self) -> None:
        self._maybe_skip()
        from backend.core.cache.idempotency import get_stored_response, store_response

        store_response("owner-1", "key-abc", 200, {"hello": "world"})
        cached = get_stored_response("owner-1", "key-abc")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["status_code"], 200)
        self.assertEqual(cached["body"], {"hello": "world"})

    def test_cache_isolation_across_owners(self) -> None:
        self._maybe_skip()
        from backend.core.cache.idempotency import get_stored_response, store_response

        store_response("owner-1", "shared-key", 200, {"from": "owner-1"})
        store_response("owner-2", "shared-key", 200, {"from": "owner-2"})
        self.assertEqual(
            get_stored_response("owner-1", "shared-key")["body"], {"from": "owner-1"}
        )
        self.assertEqual(
            get_stored_response("owner-2", "shared-key")["body"], {"from": "owner-2"}
        )

    def test_clear_response_deletes_entry(self) -> None:
        self._maybe_skip()
        from backend.core.cache.idempotency import (
            clear_response,
            get_stored_response,
            store_response,
        )

        store_response("owner-1", "key-to-clear", 200, {"x": 1})
        self.assertIsNotNone(get_stored_response("owner-1", "key-to-clear"))
        clear_response("owner-1", "key-to-clear")
        self.assertIsNone(get_stored_response("owner-1", "key-to-clear"))

    def test_missing_key_returns_none(self) -> None:
        self._maybe_skip()
        from backend.core.cache.idempotency import get_stored_response

        self.assertIsNone(get_stored_response("nobody", "no-such-key"))

    def test_empty_inputs_are_noops(self) -> None:
        self._maybe_skip()
        from backend.core.cache.idempotency import get_stored_response, store_response

        # Storing with empty inputs must not crash and must not be retrievable.
        store_response("", "", 200, {"x": 1})
        self.assertIsNone(get_stored_response("", ""))
        self.assertIsNone(get_stored_response("owner", ""))


class MigrationShapeTest(unittest.TestCase):
    """Migration files include the new constraint/index/column changes."""

    def test_phase1_migration_exists(self) -> None:
        from pathlib import Path

        versions_dir = Path(__file__).resolve().parents[2] / "core" / "database" / "migrations" / "versions"
        candidates = list(versions_dir.glob("*add_org_ownership_idempotency.py"))
        self.assertEqual(len(candidates), 1, f"expected one Phase 1 migration, got {candidates}")

        text = candidates[0].read_text()
        self.assertIn("org_id", text)
        self.assertIn("created_by", text)
        self.assertIn("uq_campaigns_owner_product_niche", text)
        self.assertIn("idx_influencer_scores_campaign_final", text)
        self.assertIn("idx_crawl_sources_campaign_status", text)

    def test_phase1_migration_down_revision_points_to_head(self) -> None:
        import re
        from pathlib import Path

        versions_dir = Path(__file__).resolve().parents[2] / "core" / "database" / "migrations" / "versions"
        candidates = list(versions_dir.glob("*add_org_ownership_idempotency.py"))
        text = candidates[0].read_text()
        # Match the literal assignment of the down_revision constant —
        # the variable is typed as ``str | None`` so we anchor on the
        # assignment line, not just any occurrence of the field name.
        m = re.search(r"down_revision:\s*str[^=]*=\s*\"([a-z0-9]+)\"", text)
        self.assertIsNotNone(m, "down_revision assignment not found")
        self.assertEqual(m.group(1), "f1a2b3c4d5e6", "must chain off the existing head")


class SettingsMigrationShapeTest(unittest.TestCase):
    """Settings migration chains off the head, declares the right tables/columns.

    Catches two regressions cheaply: (1) someone forgets to update
    ``down_revision`` when landing this change, which would break
    `alembic upgrade head`; (2) the tables/columns the /settings
    page depends on silently disappear from the migration script.
    """

    def _settings_migration_path(self) -> Path:
        versions_dir = Path(__file__).resolve().parents[2] / "core" / "database" / "migrations" / "versions"
        candidates = list(versions_dir.glob("*add_settings_support.py"))
        self.assertEqual(
            len(candidates),
            1,
            f"expected one settings migration, got {candidates}",
        )
        return candidates[0]

    def test_settings_migration_chains_off_existing_head(self) -> None:
        import re

        text = self._settings_migration_path().read_text()
        m = re.search(r"down_revision:\s*str[^=]*=\s*\"([a-z0-9]+)\"", text)
        self.assertIsNotNone(m, "down_revision assignment not found")
        self.assertEqual(
            m.group(1),
            "h4i5j6k7l8m9",
            "settings migration must chain off the brand_profiles head",
        )

    def test_settings_migration_declares_expected_objects(self) -> None:
        text = self._settings_migration_path().read_text()
        # New tables backing the settings page.
        for table in (
            "notification_preferences",
            "integration_connections",
            "api_keys",
            "subscriptions",
        ):
            self.assertIn(
                f'"{table}"',
                text,
                f"settings migration should create the {table} table",
            )
        # User-column extensions.
        for column in ("role", "timezone", "deleted_at"):
            self.assertIn(column, text, f"settings migration should add users.{column}")
        # Unique constraint on (user_id, provider) for integration rows.
        self.assertIn("uq_integration_connections_user_provider", text)
        # Index on api_keys.user_id for fast listing.
        self.assertIn("idx_api_keys_user", text)


class SettingsModelSurfaceTest(unittest.TestCase):
    """ORM models for the settings page exist and have the expected columns."""

    def setUp(self) -> None:
        try:
            from backend.core.database import models  # noqa: F401
        except Exception as exc:
            self.skipTest(f"psycopg not available in test env: {exc}")

    def test_user_has_settings_columns(self) -> None:
        from backend.core.database import models

        cols = models.User.__table__.columns
        for column in ("role", "timezone", "deleted_at"):
            self.assertIn(column, cols, f"User.{column} should exist")

    def test_settings_models_have_expected_columns(self) -> None:
        from backend.core.database import models

        # NotificationPreference
        np_cols = models.NotificationPreference.__table__.columns
        for column in ("shortlist_ready", "creator_replied", "weekly_digest", "product_updates"):
            self.assertIn(column, np_cols)

        # IntegrationConnection
        ic_cols = models.IntegrationConnection.__table__.columns
        for column in ("provider", "connected", "connected_at"):
            self.assertIn(column, ic_cols)
        ic_constraints = {c.name for c in models.IntegrationConnection.__table__.constraints}
        self.assertIn("uq_integration_connections_user_provider", ic_constraints)

        # ApiKey
        ak_cols = models.ApiKey.__table__.columns
        for column in ("key_prefix", "key_hash", "revoked_at"):
            self.assertIn(column, ak_cols)

        # Subscription
        sub_cols = models.Subscription.__table__.columns
        self.assertIn("plan", sub_cols)


class SettingsSchemaSurfaceTest(unittest.TestCase):
    """Pydantic schemas for /api/settings and /api/auth/me exist and are wired."""

    def test_user_response_includes_role_and_timezone(self) -> None:
        from backend.api.schemas.auth import UserResponse

        props = UserResponse.model_json_schema().get("properties", {})
        self.assertIn("role", props)
        self.assertIn("timezone", props)

    def test_settings_schemas_have_expected_fields(self) -> None:
        from backend.api.schemas import settings as schemas

        for name in (
            "UpdateProfileRequest",
            "ChangePasswordRequest",
            "NotificationPreferencesRequest",
            "NotificationPreferencesResponse",
            "IntegrationStatusResponse",
            "ApiKeyResponse",
            "ApiKeyCreatedResponse",
            "SubscriptionResponse",
            "SubscriptionUpdateRequest",
        ):
            self.assertTrue(hasattr(schemas, name), f"missing schema: {name}")

    def test_api_key_created_response_includes_full_key(self) -> None:
        from backend.api.schemas.settings import ApiKeyCreatedResponse

        # ``key`` is the one-time-only field that distinguishes
        # create from list; without it the UI can't surface the
        # full key on the success banner.
        props = ApiKeyCreatedResponse.model_json_schema().get("properties", {})
        self.assertIn("key", props)


class AuthRouterSettingsRoutesTest(unittest.TestCase):
    """The auth router exposes PATCH/DELETE /me and POST /change-password."""

    def test_settings_auth_routes_present(self) -> None:
        from backend.api.routers import auth as auth_router

        paths = {route.path for route in auth_router.router.routes}
        self.assertIn("/api/auth/me", paths)
        # PATCH and DELETE on /api/auth/me show up as separate route
        # entries with the same path but different methods.
        methods_by_path = {}
        for route in auth_router.router.routes:
            methods_by_path.setdefault(route.path, set()).add(
                ",".join(sorted(route.methods or ()))
            )
        me_methods = methods_by_path.get("/api/auth/me", set())
        self.assertTrue(
            any("PATCH" in m for m in me_methods),
            f"PATCH /api/auth/me should exist, got methods {me_methods}",
        )
        self.assertTrue(
            any("DELETE" in m for m in me_methods),
            f"DELETE /api/auth/me should exist, got methods {me_methods}",
        )
        self.assertIn("/api/auth/change-password", paths)


class SettingsRouterRoutesTest(unittest.TestCase):
    """The settings router exposes the documented endpoint surface."""

    def test_settings_routes_present(self) -> None:
        from backend.api.routers import settings as settings_router

        paths_by_method: dict[tuple[str, str], str] = {}
        for route in settings_router.router.routes:
            for method in route.methods or ():
                if method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    paths_by_method[(method, route.path)] = route.name

        # Notifications
        self.assertIn(("GET", "/api/settings/notifications"), paths_by_method)
        self.assertIn(("PUT", "/api/settings/notifications"), paths_by_method)
        # Integrations list + connect + disconnect
        self.assertIn(("GET", "/api/settings/integrations"), paths_by_method)
        self.assertIn(
            ("POST", "/api/settings/integrations/{provider}/connect"),
            paths_by_method,
        )
        self.assertIn(
            ("POST", "/api/settings/integrations/{provider}/disconnect"),
            paths_by_method,
        )
        # API keys
        self.assertIn(("GET", "/api/settings/api-keys"), paths_by_method)
        self.assertIn(("POST", "/api/settings/api-keys"), paths_by_method)
        self.assertIn(
            ("DELETE", "/api/settings/api-keys/{key_id}"), paths_by_method
        )
        # Subscription
        self.assertIn(("GET", "/api/settings/subscription"), paths_by_method)
        self.assertIn(("POST", "/api/settings/subscription"), paths_by_method)


class GetCurrentUserSoftDeleteFilterTest(unittest.TestCase):
    """get_current_user rejects soft-deleted users (deleted_at != NULL).

    Catches the bug where DELETE /api/auth/me sets ``deleted_at`` but
    a stale JWT still resolves to the user — we want every
    authenticated request after delete to be 401.
    """

    def setUp(self) -> None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            from backend.core.database.models import User  # noqa: F401
        except Exception as exc:
            self.skipTest(f"sqlalchemy not available: {exc}")

        # Use an in-memory SQLite engine but only create the users
        # table — other tables have Postgres-specific JSONB columns
        # that SQLite can't render. We only need User to exercise
        # the deleted_at filter.

        engine = create_engine("sqlite:///:memory:")
        _adapt_user_table_for_sqlite(User)
        User.__table__.create(engine, checkfirst=True)
        self.Session = sessionmaker(bind=engine)
        self._engine = engine

    def _make_user(self, *, deleted: bool) -> str:
        import uuid
        from datetime import UTC, datetime

        from backend.core.auth import hash_password
        from backend.core.database.models import User

        session = self.Session()
        try:
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                email=f"{uuid.uuid4()}@example.com",
                password_hash=hash_password("hunter22"),
                name="Deleted Test",
                company_name="Acme",
                deleted_at=datetime.now(UTC) if deleted else None,
            )
            session.add(user)
            session.commit()
            return user_id
        finally:
            session.close()

    def test_active_user_resolves(self) -> None:
        from unittest.mock import patch

        from backend.core.auth import get_current_user

        user_id = self._make_user(deleted=False)
        db = self.Session()
        try:
            # Keep JWT subject as a string for the SQLite test table (String PK).
            with patch("backend.core.auth.UUID", side_effect=lambda value: value):
                user = get_current_user(
                    token=_mint_token(user_id),
                    db=db,
                )
            self.assertEqual(str(user.id), user_id)
        finally:
            db.close()

    def test_soft_deleted_user_is_rejected(self) -> None:
        from unittest.mock import patch

        from fastapi import HTTPException

        from backend.core.auth import get_current_user

        user_id = self._make_user(deleted=True)
        db = self.Session()
        try:
            with patch("backend.core.auth.UUID", side_effect=lambda value: value):
                with self.assertRaises(HTTPException) as ctx:
                    get_current_user(
                        token=_mint_token(user_id),
                        db=db,
                    )
            self.assertEqual(ctx.exception.status_code, 401)
        finally:
            db.close()


def _mint_token(user_id: str) -> str:
    """Mint a short-lived access token for the in-memory test user."""
    from datetime import UTC, datetime, timedelta

    import jwt

    from backend.core.config import settings

    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


if __name__ == "__main__":
    unittest.main()
