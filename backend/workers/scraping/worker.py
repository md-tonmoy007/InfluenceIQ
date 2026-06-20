from __future__ import annotations

# IMPORTANT: create the Celery app BEFORE importing the task modules so
# the @shared_task decorators register with this worker's app instance
# rather than the central backend.core.celery.app or a previously-created one.
from backend.core.celery.factory import create_celery_app
from backend.core.celery.roles import SCRAPING

celery_app = create_celery_app(SCRAPING)

# Import the task bodies so Celery can discover them.
from backend.pipeline.tasks import execute_search, extract_content, fetch_page  # noqa: E402, F401
