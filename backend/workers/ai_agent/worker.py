from __future__ import annotations

# Use the central Celery app so @shared_task bodies register with the same
# task_routes table the API uses when calling .delay().
from backend.core.celery.app import celery_app

# Eager-import this worker's tasks so discovery is explicit at boot.
from backend.pipeline.tasks.deep import deep_analyze  # noqa: F401
from backend.pipeline.tasks.extract import resolve_identity_llm  # noqa: F401
from backend.pipeline.tasks.score import classify_brand_safety  # noqa: F401
from backend.pipeline.tasks.search import generate_queries  # noqa: F401
