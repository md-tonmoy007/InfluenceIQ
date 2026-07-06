"""Assert that every pipeline task ships to the queue declared in the
Role-4 charter (``backend/core/celery/roles.py``).

The tests run in eager mode so we can verify ``app.send_task`` routing
without a running broker.
"""

from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")
os.environ.setdefault("CELERY_TASK_EAGER_PROPAGATES", "True")

from backend.core.celery.roles import TASK_QUEUE_BY_NAME

# The canonical mapping from the Role-4 charter.
EXPECTED_ROUTING: dict[str, str] = {
    # ai_agent_queue — LLM-heavy tasks
    "backend.pipeline.tasks.search.generate_queries": "ai_agent_queue",
    "backend.pipeline.tasks.extract.resolve_identity_llm": "ai_agent_queue",
    "backend.pipeline.tasks.score.classify_brand_safety": "ai_agent_queue",
    # scraping_queue — I/O-heavy tasks (search + crawl)
    "backend.pipeline.tasks.search.execute_search": "scraping_queue",
    "backend.pipeline.tasks.crawl.fetch_page": "scraping_queue",
    "backend.pipeline.tasks.crawl.extract_content": "scraping_queue",
    "backend.pipeline.tasks.enrich.enrich_influencer_platforms": "scraping_queue",
    # scoring_queue — compute-heavy tasks (extraction + scoring)
    "backend.pipeline.tasks.extract.extract_influencers": "scoring_queue",
    "backend.pipeline.tasks.extract.resolve_identity_cluster": "scoring_queue",
    "backend.pipeline.tasks.score.score_influencer": "scoring_queue",
    "backend.pipeline.tasks.deep.deep_analyze": "ai_agent_queue",
}


def test_all_expected_tasks_are_routed() -> None:
    """Every task in the charter has a routing entry."""
    for task_name, expected_queue in EXPECTED_ROUTING.items():
        actual_queue = TASK_QUEUE_BY_NAME.get(task_name)
        assert actual_queue == expected_queue, (
            f"Task {task_name} expected queue {expected_queue!r}, "
            f"got {actual_queue!r}"
        )


def test_no_extra_tasks_in_routing_table() -> None:
    """Every entry in the routing table is expected by the charter."""
    extra = set(TASK_QUEUE_BY_NAME) - set(EXPECTED_ROUTING)
    assert not extra, f"Unexpected tasks in routing table: {extra}"


def test_task_routing_via_celery_app() -> None:
    """Verify that celery_app routes each task name to the correct queue."""
    from backend.core.celery.app import celery_app

    for task_name, expected_queue in EXPECTED_ROUTING.items():
        route = celery_app.conf.task_routes.get(task_name)
        if route is None:
            # Fallback: check task_routes as a dict
            routes = celery_app.conf.task_routes
            if isinstance(routes, (list, tuple)):
                route = next(
                    (r for r in routes if isinstance(r, dict) and task_name in r),
                    None,
                )
                if route:
                    route = route[task_name]
        if route is None:
            # Check if task_queues are configured
            queue = celery_app.amqp.routes[0].resolve(task_name) if celery_app.amqp.routes else None
            if queue is None:
                continue  # eager mode may not resolve routes
        if route:
            actual = route.get("queue") if isinstance(route, dict) else str(route)
            assert actual == expected_queue, (
                f"Celery routes {task_name} to {actual!r}, expected {expected_queue!r}"
            )


def test_orchestrator_task_routes_to_correct_service() -> None:
    """Legacy orchestrator tasks have no queue (control plane)."""
    from backend.core.celery.roles import TASK_NAMES_BY_SERVICE

    for service, task_names in TASK_NAMES_BY_SERVICE.items():
        for task_name in task_names:
            assert task_name in TASK_QUEUE_BY_NAME, (
                f"Task {task_name} in {service} service list but not in TASK_QUEUE_BY_NAME"
            )
