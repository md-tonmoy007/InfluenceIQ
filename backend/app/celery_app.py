from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "influenceiq",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.search",
        "app.tasks.crawl",
        "app.tasks.extract",
        "app.tasks.score",
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
    task_routes={
        "app.tasks.search.*":  {"queue": "search_queue"},
        "app.tasks.crawl.*":   {"queue": "crawl_queue"},
        "app.tasks.extract.*": {"queue": "extract_queue"},
        "app.tasks.score.*":   {"queue": "score_queue"},
    },
    task_default_retry_delay=2,
    task_annotations={
        "*": {
            "max_retries": 3,
            "retry_backoff": True,
            "retry_backoff_max": 60,
            "retry_jitter": True,
        }
    },
)
