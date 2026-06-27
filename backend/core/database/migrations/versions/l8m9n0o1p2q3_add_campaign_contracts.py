"""add_campaign_contracts

Adds ``campaign_contracts`` for outreach/contract tracking per campaign.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l8m9n0o1p2q3"
down_revision: str | None = "k7l8m9n0o1p2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "campaign_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "influencer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("influencers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="contracted"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "campaign_id",
            "influencer_id",
            name="uq_campaign_contracts_campaign_influencer",
        ),
    )
    op.create_index(
        "idx_campaign_contracts_campaign_id",
        "campaign_contracts",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "idx_campaign_contracts_created_by_campaign",
        "campaign_contracts",
        ["created_by", "campaign_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_campaign_contracts_created_by_campaign", table_name="campaign_contracts")
    op.drop_index("idx_campaign_contracts_campaign_id", table_name="campaign_contracts")
    op.drop_table("campaign_contracts")
