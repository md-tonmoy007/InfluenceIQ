"""Lifecycle / startup validation unit tests.

Pure unit tests — no DB, no Redis, no FastAPI. Imports ``settings`` so
the test must be run with the same env vars the Makefile passes to
``test-unit``.
"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


class LifecycleValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        # Reset the settings singleton so each test sees a fresh load.
        from backend.core import config as config_module
        from backend.core import lifecycle

        config_module.settings = config_module.Settings()
        lifecycle.settings = config_module.settings

    def test_baseline_env_passes(self) -> None:
        from backend.core.lifecycle import validate_settings

        summary = validate_settings()
        self.assertIn("app_env", summary)

    def test_invalid_database_url_rejected(self) -> None:
        from backend.core.config import Settings
        from backend.core.lifecycle import StartupValidationError, validate_settings

        s = Settings(
            DATABASE_URL="ftp://x",
            REDIS_URL="redis://localhost:6379/0",
            CELERY_BROKER_URL="redis://localhost:6379/0",
            CELERY_RESULT_BACKEND="redis://localhost:6379/1",
            REDIS_STATE_DB="redis://localhost:6379/2",
            QDRANT_URL="http://localhost:6333",
        )
        from backend.core import lifecycle

        lifecycle.settings = s
        with self.assertRaises(StartupValidationError) as ctx:
            validate_settings()
        self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_invalid_app_env_rejected(self) -> None:
        from backend.core.config import Settings
        from backend.core.lifecycle import StartupValidationError, validate_settings

        s = Settings(
            APP_ENV="production",  # not in the allow-list
            DATABASE_URL="postgresql+psycopg://x:x@localhost:5432/x",
            REDIS_URL="redis://localhost:6379/0",
            CELERY_BROKER_URL="redis://localhost:6379/0",
            CELERY_RESULT_BACKEND="redis://localhost:6379/1",
            REDIS_STATE_DB="redis://localhost:6379/2",
            QDRANT_URL="http://localhost:6333",
        )
        from backend.core import lifecycle

        lifecycle.settings = s
        with self.assertRaises(StartupValidationError) as ctx:
            validate_settings()
        self.assertIn("APP_ENV", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
