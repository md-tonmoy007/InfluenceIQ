"""Pipeline 1-20 orchestrator.

:func:`run_role5_pipeline` is the single entry point that drives the
role-5 service end-to-end. It composes the existing extraction,
identity, detection, analysis, and scoring modules in the order
documented in ``Role-5-Implementation.md`` and returns the full
backend/frontend contract.

The orchestrator is intentionally **stateless** and **deterministic**
- it accepts a single ``candidate`` dict and an optional ``campaign``
context, and returns a JSON-serializable result. No globals, no I/O,
no LLM calls. The Celery adapters in ``backend/pipeline/tasks/`` are the
only place that talks to Redis.
"""

from backend.pipeline.orchestrator.pipeline import (
    Role5PipelineResult,
    run_role5_pipeline,
    trust_grade_to_confidence,
)

__all__ = ["Role5PipelineResult", "run_role5_pipeline", "trust_grade_to_confidence"]
