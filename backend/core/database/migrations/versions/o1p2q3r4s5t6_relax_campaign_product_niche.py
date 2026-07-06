"""relax_campaign_product_niche

Campaigns now capture one free-text ``search_query`` description instead
of separate product/niche fields. Drops the
``uq_campaigns_owner_product_niche`` unique index (dedup now relies
solely on the Idempotency-Key header path) and relaxes ``product``/
``niche`` to nullable so new campaigns can omit them.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "o1p2q3r4s5t6"
down_revision: str | None = "n0o1p2q3r4s5"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # This was created via op.create_index(..., unique=True) in
    # g2h3i4j5k6l7, i.e. it's a unique index, not a table constraint —
    # drop_constraint() can't see it.
    op.drop_index("uq_campaigns_owner_product_niche", table_name="campaigns")
    op.alter_column("campaigns", "product", existing_type=sa.String(), nullable=True)
    op.alter_column("campaigns", "niche", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Note: fails if any row has a null product/niche by the time this runs.
    op.alter_column("campaigns", "niche", existing_type=sa.String(), nullable=False)
    op.alter_column("campaigns", "product", existing_type=sa.String(), nullable=False)
    op.create_index(
        "uq_campaigns_owner_product_niche",
        "campaigns",
        ["created_by", "product", "niche"],
        unique=True,
    )
