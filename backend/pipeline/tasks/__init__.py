"""Celery task bodies for the role-5 influence-discovery pipeline.

The task chain is intentionally split into four modules so the
per-service Celery workers can subscribe to a coherent subset
(``backend.pipeline.tasks.search`` for ai-agent + scraping, etc.):

* ``backend.pipeline.tasks.search``   — :func:`generate_queries`, :func:`execute_search`
* ``backend.pipeline.tasks.crawl``    — :func:`fetch_page`, :func:`extract_content`
* ``backend.pipeline.tasks.extract``  — :func:`extract_influencers`, :func:`resolve_identity_llm`
* ``backend.pipeline.tasks.score``    — :func:`score_influencer`, :func:`classify_brand_safety`

Each module's tasks are wired to the queues declared in
:mod:`backend.core.celery.roles` via the ``task_routes`` table on
:data:`backend.core.celery.app.celery_app`. The chain entry point is
:func:`start_pipeline` — call it from the API once a campaign row
has been created.
"""

from __future__ import annotations

from backend.pipeline.tasks.crawl import extract_content, fetch_page
from backend.pipeline.tasks.extract import extract_influencers, resolve_identity_llm
from backend.pipeline.tasks.score import classify_brand_safety, score_influencer
from backend.pipeline.tasks.search import execute_search, generate_queries


def start_pipeline(campaign_id: str) -> dict:
    """Kick off the role-5 pipeline for ``campaign_id``.

    The chain is:

    ``generate_queries`` → (per query) ``execute_search``
        → (per result) ``fetch_page`` → ``extract_content``
        → ``extract_influencers`` → (per new influencer)
        ``score_influencer`` → (per severe brand-safety flag)
        ``classify_brand_safety``.

    The first task is dispatched asynchronously. Subsequent steps
    are dispatched inside the task bodies so the chain runs across
    multiple workers in parallel.
    """
    async_result = generate_queries.delay(campaign_id)
    return {
        "campaign_id": campaign_id,
        "started": True,
        "task_id": async_result.id,
    }


__all__ = [
    "classify_brand_safety",
    "execute_search",
    "extract_content",
    "extract_influencers",
    "fetch_page",
    "generate_queries",
    "resolve_identity_llm",
    "score_influencer",
    "start_pipeline",
]
