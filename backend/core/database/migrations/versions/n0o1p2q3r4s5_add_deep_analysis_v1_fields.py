"""add_deep_analysis_v1_fields

Extends ``deep_analysis_runs`` with post limits, comment limits,
coverage summary, report version, and cache expiry for the v1 staged
deep-analysis workflow.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n0o1p2q3r4s5"
down_revision: str | None = "m9n0o1p2q3r4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("deep_analysis_runs", sa.Column("requested_post_limit", sa.Integer(), nullable=False, server_default="20"))
    op.add_column("deep_analysis_runs", sa.Column("requested_comment_limit", sa.Integer(), nullable=False, server_default="200"))
    op.add_column("deep_analysis_runs", sa.Column("coverage_summary", postgresql.JSONB(), nullable=True))
    op.add_column("deep_analysis_runs", sa.Column("report_version", sa.String(length=32), nullable=False, server_default="v1"))
    op.add_column("deep_analysis_runs", sa.Column("cache_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("deep_analysis_runs", "cache_expires_at")
    op.drop_column("deep_analysis_runs", "report_version")
    op.drop_column("deep_analysis_runs", "coverage_summary")
    op.drop_column("deep_analysis_runs", "requested_comment_limit")
    op.drop_column("deep_analysis_runs", "requested_post_limit")
