from __future__ import annotations

# IMPORTANT: create the Celery app BEFORE importing the task modules so
# the @shared_task decorators register with this worker's app instance
# rather than the central app.celery_app or a previously-created one.
from app.celery_factory import create_celery_app
from app.service_roles import SCRAPING_SERVICE

celery_app = create_celery_app(SCRAPING_SERVICE)

# Import the task bodies so Celery can discover them.
from app.tasks import execute_search, extract_content, fetch_page  # noqa: E402, F401
