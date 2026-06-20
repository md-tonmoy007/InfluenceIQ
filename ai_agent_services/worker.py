from __future__ import annotations

# IMPORTANT: create the Celery app BEFORE importing the task modules so
# the @shared_task decorators register with this worker's app instance
# rather than the central app.celery_app or a previously-created one.
from app.celery_factory import create_celery_app
from app.service_roles import AI_AGENT_SERVICE

celery_app = create_celery_app(AI_AGENT_SERVICE)

# Import the task bodies so Celery can discover them.
from app.tasks import (  # noqa: E402, F401
    classify_brand_safety,
    generate_queries,
    resolve_identity_llm,
)
