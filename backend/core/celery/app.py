from __future__ import annotations

from celery import Celery

from backend.core.celery.roles import TASK_QUEUE_BY_NAME
from backend.core.config import settings

# Central Celery app — shared by the API process (for ``.delay()`` dispatch
# with correct queue routing) and by the workers (which prefer
# :func:`backend.core.celery.factory.create_celery_app` for per-service isolation).
celery_app = Celery(
    "influenceiq",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.pipeline.tasks.search",
        "backend.pipeline.tasks.crawl",
        "backend.pipeline.tasks.extract",
        "backend.pipeline.tasks.score",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=21600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=2,
    # Route every declared task to its service's queue so ``.delay()`` from
    # the API lands in the right worker's inbox even without explicit
    # ``queue=`` arguments.
    task_routes={
        task_name: {"queue": queue}
        for task_name, queue in TASK_QUEUE_BY_NAME.items()
    },
    task_annotations={
        "*": {
            "max_retries": 3,
            "retry_backoff": True,
            "retry_backoff_max": 60,
            "retry_jitter": True,
        }
    },
)

# Ensure @shared_task decorators in pipeline.tasks.* bind here so .delay()
# from the API uses task_routes (ai_agent_queue, scraping_queue, etc.)
# instead of the broker default "celery" queue that no worker consumes.
celery_app.set_default()
