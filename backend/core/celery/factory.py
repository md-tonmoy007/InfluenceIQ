from __future__ import annotations

from celery import Celery

from backend.core.celery.roles import TASK_NAMES_BY_SERVICE
from backend.core.config import settings


def create_celery_app(service_role: str) -> Celery:
    task_names = TASK_NAMES_BY_SERVICE.get(service_role, [])
    task_routes = {name: {"queue": f"{service_role}_queue"} for name in task_names}

    app = Celery(
        f"influenceiq_{service_role}",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    app.conf.update(
        broker_connection_retry_on_startup=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        result_expires=21600,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_routes=task_routes,
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

    return app
