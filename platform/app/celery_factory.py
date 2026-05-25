from __future__ import annotations

from celery import Celery

from app.config import settings
from app.service_roles import ALL_TASK_MODULES, TASK_MODULES_BY_SERVICE, TASK_QUEUE_BY_NAME


def create_celery_app(service_name: str, include_modules: list[str] | None = None) -> Celery:
    include = include_modules or TASK_MODULES_BY_SERVICE.get(service_name, ALL_TASK_MODULES)

    celery_app = Celery(
        service_name,
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=include,
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
        task_routes={task_name: {"queue": queue_name} for task_name, queue_name in TASK_QUEUE_BY_NAME.items()},
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

    return celery_app
