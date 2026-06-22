"""add_brand_profiles

Adds the ``brand_profiles`` table backing the onboarding wizard
(POST/GET /api/onboarding). One row per user, created/updated by the
"Tell us about your brand" -> "Goals" -> "Platforms" steps in the
frontend onboarding flow.

Revision ID: h4i5j6k7l8m9
Revises: g2h3i4j5k6l7
Create Date: 2026-06-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h4i5j6k7l8m9"
down_revision: str | None = "g2h3i4j5k6l7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brand_name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("company_size", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("goals", postgresql.JSONB(), nullable=True),
        sa.Column("platforms", postgresql.JSONB(), nullable=True),
        sa.Column("monthly_budget", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_brand_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("brand_profiles")
