from __future__ import annotations

# IMPORTANT: create the Celery app BEFORE importing the task modules so
# the @shared_task decorators register with this worker's app instance
# rather than the central backend.core.celery.app or a previously-created one.
from backend.core.celery.factory import create_celery_app
from backend.core.celery.roles import AI_AGENT

celery_app = create_celery_app(AI_AGENT)

# Import the task bodies so Celery can discover them.
from backend.pipeline.tasks import (  # noqa: E402, F401
    classify_brand_safety,
    generate_queries,
    resolve_identity_llm,
)
