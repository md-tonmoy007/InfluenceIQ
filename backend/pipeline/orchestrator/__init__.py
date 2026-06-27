"""Pipeline orchestrator — role-4 entry point.

:func:`run_role4_pipeline` is the single entry point that drives the
pipeline intelligence service end-to-end. It composes extraction,
identity, detection, analysis, and scoring modules and returns the full
backend/frontend contract.

The orchestrator is intentionally **stateless** and **deterministic**
— it accepts a single ``candidate`` dict and an optional ``campaign``
context, and returns a JSON-serializable result. No globals, no I/O,
no LLM calls. The Celery adapters in ``backend/pipeline/tasks/`` are the
only place that talks to Redis.
"""

from backend.pipeline.orchestrator.pipeline import (
    Role4PipelineResult,
    run_role4_pipeline,
    trust_grade_to_confidence,
)

__all__ = ["Role4PipelineResult", "run_role4_pipeline", "trust_grade_to_confidence"]
