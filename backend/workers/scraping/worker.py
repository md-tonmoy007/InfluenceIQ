from __future__ import annotations

from backend.core.celery.app import celery_app

from backend.pipeline.tasks.crawl import extract_content, fetch_page  # noqa: F401
from backend.pipeline.tasks.enrich import enrich_influencer_platforms_task  # noqa: F401
from backend.pipeline.tasks.search import execute_search  # noqa: F401
