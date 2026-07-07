"""add_deep_analysis_run_current_stage

Adds a ``current_stage`` column to ``deep_analysis_runs`` so the polling
endpoint and the report page can render an honest per-stage progress
indicator. The column is populated by :mod:`backend.pipeline.tasks.deep`
between each stage boundary and reflects the last completed stage
(``social``, ``comments``, ``trends``, ``synthesizing``, ``done``).

The previous implementation committed the run row only at the very end
of the Celery task, so the polling endpoint could not distinguish "the
worker is between stages" from "the worker hasn't started yet". This
column makes that distinction cheap and observable.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "q3r4s5t6u7v8"
down_revision: str | None = "p2q3r4s5t6u7"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "deep_analysis_runs",
        sa.Column("current_stage", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deep_analysis_runs", "current_stage")
