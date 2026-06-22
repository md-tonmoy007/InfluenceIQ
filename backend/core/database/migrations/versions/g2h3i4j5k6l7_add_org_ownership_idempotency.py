"""add_org_ownership_idempotency

Adds ownership columns to ``campaigns`` (org_id, created_by) plus indexes
that materially help the ranking endpoint (final_score DESC) and the
pipeline status aggregation (campaign_id, status).

Also enforces idempotency at the database layer via a UNIQUE constraint on
(created_by, product, niche) so duplicate ``POST /api/campaigns`` calls
made by the same user with the same payload cannot enqueue duplicate
pipelines.

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-21 17:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g2h3i4j5k6l7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # campaigns: ownership columns
    # ------------------------------------------------------------------
    # Both columns are nullable to preserve the existing demo data path
    # (seeded campaigns are inserted via /api/demo/seed which bypasses
    # auth and may run without a JWT subject).
    op.add_column(
        "campaigns",
        sa.Column("org_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "created_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------
    # campaigns: idempotency unique constraint
    # ------------------------------------------------------------------
    # Natural-key uniqueness scoped per-owner so two different users can
    # legitimately run the same product/niche concurrently. NULL
    # created_by rows are treated as distinct by Postgres; legacy
    # demo-seeded rows without a created_by owner will not collide.
    op.create_index(
        "idx_campaigns_created_by",
        "campaigns",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        "uq_campaigns_owner_product_niche",
        "campaigns",
        ["created_by", "product", "niche"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # ranking endpoint: index that backs "ORDER BY final_score DESC
    # WHERE campaign_id = ?" — the hot query for /campaigns/{id}/influencers
    # ------------------------------------------------------------------
    op.create_index(
        "idx_influencer_scores_campaign_final",
        "influencer_scores",
        ["campaign_id", sa.text("final_score DESC")],
        unique=False,
    )

    # ------------------------------------------------------------------
    # pipeline status aggregation: refresh_campaign_status counts
    # crawl_sources by status; the (campaign_id, status) compound
    # index lets that aggregate run as an index-only scan.
    # ------------------------------------------------------------------
    op.create_index(
        "idx_crawl_sources_campaign_status",
        "crawl_sources",
        ["campaign_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_crawl_sources_campaign_status", table_name="crawl_sources")
    op.drop_index("idx_influencer_scores_campaign_final", table_name="influencer_scores")

    op.drop_index("uq_campaigns_owner_product_niche", table_name="campaigns")
    op.drop_index("idx_campaigns_created_by", table_name="campaigns")

    op.drop_column("campaigns", "created_by")
    op.drop_column("campaigns", "org_id")
