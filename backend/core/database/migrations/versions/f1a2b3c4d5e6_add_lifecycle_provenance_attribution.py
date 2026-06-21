"""add_lifecycle_provenance_attribution

Revision ID: f1a2b3c4d5e6
Revises: b32203e0ccc5
Create Date: 2026-06-21 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "b32203e0ccc5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("status", sa.String(), nullable=False, server_default="pending"))
    op.add_column("campaigns", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("campaigns", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column("campaigns", sa.Column("failed_at", sa.DateTime(), nullable=True))
    op.add_column("campaigns", sa.Column("failure_reason", sa.Text(), nullable=True))

    op.add_column("crawl_sources", sa.Column("html", sa.Text(), nullable=True))

    op.add_column(
        "influencer_scores",
        sa.Column("signal_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("influencer_scores", sa.Column("risk_category", sa.String(), nullable=True))
    op.add_column("influencer_scores", sa.Column("detection_category", sa.String(), nullable=True))
    op.add_column(
        "influencer_scores",
        sa.Column("positive_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "influencer_scores",
        sa.Column("negative_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "influencer_scores",
        sa.Column("source_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "crawl_source_influencers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("crawl_source_id", sa.UUID(), nullable=False),
        sa.Column("influencer_id", sa.UUID(), nullable=False),
        sa.Column("mention_id", sa.String(), nullable=True),
        sa.Column("mention", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["crawl_source_id"], ["crawl_sources.id"]),
        sa.ForeignKeyConstraint(["influencer_id"], ["influencers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "crawl_source_id",
            "influencer_id",
            "mention_id",
            name="uq_crawl_source_influencer_mention",
        ),
    )
    op.create_index(
        "idx_crawl_source_influencers_source",
        "crawl_source_influencers",
        ["crawl_source_id"],
        unique=False,
    )
    op.create_index(
        "idx_crawl_source_influencers_influencer",
        "crawl_source_influencers",
        ["influencer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_crawl_source_influencers_influencer", table_name="crawl_source_influencers")
    op.drop_index("idx_crawl_source_influencers_source", table_name="crawl_source_influencers")
    op.drop_table("crawl_source_influencers")

    op.drop_column("influencer_scores", "source_provenance")
    op.drop_column("influencer_scores", "negative_reasons")
    op.drop_column("influencer_scores", "positive_reasons")
    op.drop_column("influencer_scores", "detection_category")
    op.drop_column("influencer_scores", "risk_category")
    op.drop_column("influencer_scores", "signal_scores")

    op.drop_column("crawl_sources", "html")

    op.drop_column("campaigns", "failure_reason")
    op.drop_column("campaigns", "failed_at")
    op.drop_column("campaigns", "completed_at")
    op.drop_column("campaigns", "started_at")
    op.drop_column("campaigns", "status")
