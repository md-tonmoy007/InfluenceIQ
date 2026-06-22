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
:data:`backend.core.celery.app.celery_app`. The chain entry points
are :func:`start_pipeline` (legacy alias) and
:func:`backend.pipeline.tasks.orchestrator.start_campaign` —
call either from the API once a campaign row has been created.

Lazy re-exports
---------------
The task modules transitively import the SQLAlchemy ORM models, which
in turn instantiate the database engine at import time. To keep
``from backend.pipeline.tasks import orchestrator`` (and similar
selective imports) lightweight for unit tests that don't need the
full task graph, the public names below are re-exported lazily via
PEP 562 ``__getattr__``. Importing this package does **not** trigger
import of every task module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.pipeline.tasks.crawl import extract_content, fetch_page
    from backend.pipeline.tasks.extract import extract_influencers, resolve_identity_llm
    from backend.pipeline.tasks.orchestrator import cancel_campaign, start_campaign
    from backend.pipeline.tasks.score import classify_brand_safety, score_influencer
    from backend.pipeline.tasks.search import execute_search, generate_queries


# Mapping of public name -> (owning submodule, attribute name). When
# the test framework or a worker boots and asks for one of these,
# the import is performed on demand. This avoids the eager
# ``create_engine(...)`` side-effect that ``backend.core.database.session``
# would otherwise trigger whenever this package is imported.
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "extract_content": ("backend.pipeline.tasks.crawl", "extract_content"),
    "fetch_page": ("backend.pipeline.tasks.crawl", "fetch_page"),
    "extract_influencers": (
        "backend.pipeline.tasks.extract",
        "extract_influencers",
    ),
    "resolve_identity_llm": (
        "backend.pipeline.tasks.extract",
        "resolve_identity_llm",
    ),
    "classify_brand_safety": (
        "backend.pipeline.tasks.score",
        "classify_brand_safety",
    ),
    "score_influencer": ("backend.pipeline.tasks.score", "score_influencer"),
    "execute_search": ("backend.pipeline.tasks.search", "execute_search"),
    "generate_queries": ("backend.pipeline.tasks.search", "generate_queries"),
    "start_campaign": (
        "backend.pipeline.tasks.orchestrator",
        "start_campaign",
    ),
    "cancel_campaign": (
        "backend.pipeline.tasks.orchestrator",
        "cancel_campaign",
    ),
}


def __getattr__(name: str) -> Any:
    """Resolve lazy exports on first access (PEP 562)."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'backend.pipeline.tasks' has no attribute {name!r}")
    module_path, attr = target
    import importlib

    module = importlib.import_module(module_path)
    value = getattr(module, attr)
    globals()[name] = value  # cache for subsequent lookups
    return value


def start_pipeline(campaign_id: str) -> dict:
    """Backwards-compatible alias for :func:`start_campaign`.

    The original entry point lived in this module. External scripts
    (and the existing tests) still import :func:`start_pipeline` so
    we keep it as a one-line shim. New code should prefer the
    canonical name from :mod:`backend.pipeline.tasks.orchestrator`.
    """
    # Import the canonical entry point directly to bypass the lazy
    # ``__getattr__`` (this function is a callable, not a module
    # attribute, so PEP 562 module-level getattr doesn't fire here).
    from backend.pipeline.tasks.orchestrator import start_campaign as _start_campaign

    return _start_campaign(campaign_id)


__all__ = [
    "cancel_campaign",
    "classify_brand_safety",
    "execute_search",
    "extract_content",
    "extract_influencers",
    "fetch_page",
    "generate_queries",
    "resolve_identity_llm",
    "score_influencer",
    "start_campaign",
    "start_pipeline",
]
