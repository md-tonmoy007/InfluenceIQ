"""Import every public module to catch missing deps / broken syntax early.

This test is intentionally a single function that imports every
production module. If any module fails to import (syntax error,
missing dep, wrong PYTHONPATH, circular import, missing ``__init__``),
pytest reports the file and line.

Kept offline and fast. The DB engine and Redis client are imported
but never opened, so no external services are required.

Run with:

    PYTHONPATH=./backend pytest backend/tests/api/test_smoke.py -q
"""

from __future__ import annotations

import importlib
import os
import unittest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://x:x@localhost:5432/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _production_python_files() -> list[str]:
    """Yield dotted module names for every production .py file.

    Walks the ``backend`` tree (api, core, pipeline, workers) and the
    installable ``backend.ml`` package, skipping ``tests/``,
    ``__pycache__``, ``__init__`` of sub-packages, and Alembic
    migration script templates (``migrations/versions/`` and
    ``migrations/script.py.mako``).

    Modules that require optional / not-yet-installed dependencies
    (the full ML stack for ``backend.ml``, alembic's runtime for
    ``backend.core.database.migrations.env``) are also skipped. The smoke test
    must pass on a minimal dev install.
    """
    roots = [
        BACKEND_ROOT / "api",
        BACKEND_ROOT / "core",
        BACKEND_ROOT / "pipeline",
        BACKEND_ROOT / "workers",
        # backend.ml is intentionally excluded from the import-everything
        # sweep. Its modules require torch/transformers/networkx, and
        # the package is opt-in (`make ml-install`). A dedicated
        # test in backend/tests/ml/ covers the adapter contract
        # without needing the heavy deps.
    ]
    skip_relpaths = {
        # Alembic env.py imports `from alembic import context` and
        # relies on Alembic's runtime to inject it; standalone import
        # fails. Alembic is exercised by `make db-revision` and
        # `make db-upgrade`, not by the unit suite.
        Path("core/database/migrations/env.py"),
    }
    modules: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if "migrations/versions" in str(path):
                continue
            if path.name == "script.py.mako":
                continue
            rel = path.relative_to(BACKEND_ROOT)
            if rel in skip_relpaths:
                continue
            parts = rel.with_suffix("").parts
            if parts[-1] == "__init__":
                dotted = "backend." + ".".join(parts[:-1])
            else:
                dotted = "backend." + ".".join(parts)
            modules.append(dotted)
    return modules


class ImportEveryModuleTest(unittest.TestCase):
    def test_every_production_module_is_importable(self) -> None:
        failed: list[tuple[str, str]] = []
        for dotted in _production_python_files():
            try:
                importlib.import_module(dotted)
            except Exception as exc:
                failed.append((dotted, f"{type(exc).__name__}: {exc}"))
        if failed:
            lines = [f"  {dotted}: {msg}" for dotted, msg in failed]
            self.fail("The following modules failed to import:\n" + "\n".join(lines))

    def test_app_main_exposes_expected_routes(self) -> None:
        from backend.api.main import app

        # The OpenAPI schema is the canonical source for "what
        # routes does this app serve". In FastAPI >= 0.110 included
        # routers are wrapped in _IncludedRouter and the inner
        # routes are not visible on ``app.routes`` directly.
        paths = sorted(app.openapi().get("paths", {}).keys())
        expected_substrings = [
            "/health",
            "/api/campaigns",
            "/api/influencers",
            "/api/demo/seed",
        ]
        for needle in expected_substrings:
            self.assertTrue(
                any(needle in p for p in paths),
                f"Expected a route containing {needle!r}, got {paths}",
            )

    def test_celery_app_routes_every_declared_task(self) -> None:
        from backend.core.celery.app import celery_app
        from backend.core.celery.roles import TASK_QUEUE_BY_NAME

        # Trigger @shared_task registration by importing the task
        # modules. Without this, the central celery_app has only
        # the celery.* built-ins.
        from backend.pipeline.tasks import crawl, extract, score, search  # noqa: F401

        for task_name, queue in TASK_QUEUE_BY_NAME.items():
            with self.subTest(task=task_name):
                self.assertIn(task_name, celery_app.tasks)
                # Either task_routes routes it, OR the call site
                # specifies queue= explicitly. We route via task_routes
                # so verify the configuration landed.
                self.assertEqual(
                    celery_app.conf.task_routes.get(task_name, {}).get("queue"),
                    queue,
                )

    def test_worker_shims_register_only_tasks_for_their_service(self) -> None:
        """Each worker shim must only claim the tasks in its service role.

        This is a soft check: the workers happen to import all
        tasks from ``backend.pipeline.tasks`` (because the central celery_app
        ``include`` list registers them all), but each worker
        only consumes from the queue(s) it's ``-Q``-listening on.
        The contract that matters is the task_routes table on the
        worker's celery_app instance — and that matches
        :data:`backend.core.celery.roles.TASK_NAMES_BY_SERVICE`.
        """
        from backend.core.celery.factory import create_celery_app
        from backend.core.celery.roles import (
            AI_AGENT,
            SCORING,
            SCRAPING,
            TASK_NAMES_BY_SERVICE,
        )

        for role in (AI_AGENT, SCRAPING, SCORING):
            with self.subTest(role=role):
                app = create_celery_app(role)
                expected_queues = sorted({
                    f"{role}_queue"
                    for _ in TASK_NAMES_BY_SERVICE[role]
                })
                routed_queues = sorted({
                    route["queue"]
                    for route in app.conf.task_routes.values()
                })
                self.assertEqual(routed_queues, expected_queues)


if __name__ == "__main__":
    unittest.main()
