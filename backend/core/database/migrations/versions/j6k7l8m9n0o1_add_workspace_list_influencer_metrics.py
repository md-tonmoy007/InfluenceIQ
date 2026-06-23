"""add_workspace_list_influencer_metrics

Adds the durable schema that backs the user-scoped workspace shell:

* ``campaigns`` gains:
    - ``campaign_name`` (nullable) — display label set by the brief
      form or search bar.
    - ``entry_point`` (nullable, default ``"brief_form"``) — origin of
      the campaign so the dashboard and briefs list can group by
      submission channel.
    - ``search_query`` (nullable) — raw text the user typed into the
      discover/topbar search. Persisted so "recent searches" can
      show the actual query string and the campaign can be
      re-opened.
    - ``brief_snapshot`` (JSONB, nullable) — typed capture of the
      brief form fields (ages, locations, interests, etc.). Lets the
      shortlist/discover pages show the original brief inputs
      without re-deriving them from the ``goals`` / ``target_audience``
      prose blob.
    - ``updated_at`` (default now()) — for ordering/activity feeds.

* ``influencers`` gains nullable per-platform metric columns:
    - ``primary_platform`` (str)
    - ``primary_handle`` (str)
    - ``follower_count`` (int)
    - ``engagement_rate`` (float)
    - ``avg_views`` (int)
    - ``primary_category`` (str)
    - ``primary_location`` (str)

  These are best-effort, derived by the pipeline where data
  exists; missing values stay ``NULL`` and the frontend renders
  a "—" rather than fabricating zeros.

* ``saved_lists`` — one row per user-curated collection.
* ``saved_list_items`` — junction table joining lists to
  influencers, with a ``match_score_snapshot`` and a
  ``source_campaign_id`` so a list remembers where the creator
  came from. Unique on ``(list_id, influencer_id, source_campaign_id)``
  so the same creator can be re-added from a different campaign.

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-06-23 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j6k7l8m9n0o1"
down_revision: str | None = "i5j6k7l8m9n0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # campaigns: workspace metadata
    # ------------------------------------------------------------------
    op.add_column(
        "campaigns",
        sa.Column("campaign_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "entry_point",
            sa.String(length=32),
            nullable=True,
            server_default="brief_form",
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column("search_query", sa.Text(), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("brief_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "campaigns",
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # Backfill entry_point for legacy rows so the new dashboard code
    # path never sees a NULL on existing data.
    op.execute("UPDATE campaigns SET entry_point = 'brief_form' WHERE entry_point IS NULL")

    op.create_index(
        "idx_campaigns_entry_point",
        "campaigns",
        ["entry_point"],
        unique=False,
    )
    op.create_index(
        "idx_campaigns_status_created",
        "campaigns",
        ["created_by", "status", sa.text("created_at DESC")],
        unique=False,
    )

    # ------------------------------------------------------------------
    # influencers: best-effort metric columns
    # ------------------------------------------------------------------
    op.add_column(
        "influencers",
        sa.Column("primary_platform", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "influencers",
        sa.Column("primary_handle", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "influencers",
        sa.Column("follower_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "influencers",
        sa.Column("engagement_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "influencers",
        sa.Column("avg_views", sa.Integer(), nullable=True),
    )
    op.add_column(
        "influencers",
        sa.Column("primary_category", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "influencers",
        sa.Column("primary_location", sa.String(length=128), nullable=True),
    )

    # ------------------------------------------------------------------
    # saved_lists + saved_list_items
    # ------------------------------------------------------------------
    op.create_table(
        "saved_lists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_saved_lists_user", "saved_lists", ["user_id"], unique=False)

    op.create_table(
        "saved_list_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "list_id",
            sa.UUID(),
            sa.ForeignKey("saved_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "influencer_id",
            sa.UUID(),
            sa.ForeignKey("influencers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_campaign_id",
            sa.UUID(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("match_score_snapshot", sa.Float(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "list_id",
            "influencer_id",
            "source_campaign_id",
            name="uq_saved_list_items_list_influencer_source",
        ),
    )
    op.create_index(
        "idx_saved_list_items_list",
        "saved_list_items",
        ["list_id"],
        unique=False,
    )
    op.create_index(
        "idx_saved_list_items_influencer",
        "saved_list_items",
        ["influencer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_saved_list_items_influencer", table_name="saved_list_items")
    op.drop_index("idx_saved_list_items_list", table_name="saved_list_items")
    op.drop_table("saved_list_items")
    op.drop_index("idx_saved_lists_user", table_name="saved_lists")
    op.drop_table("saved_lists")

    op.drop_column("influencers", "primary_location")
    op.drop_column("influencers", "primary_category")
    op.drop_column("influencers", "avg_views")
    op.drop_column("influencers", "engagement_rate")
    op.drop_column("influencers", "follower_count")
    op.drop_column("influencers", "primary_handle")
    op.drop_column("influencers", "primary_platform")

    op.drop_index("idx_campaigns_status_created", table_name="campaigns")
    op.drop_index("idx_campaigns_entry_point", table_name="campaigns")
    op.drop_column("campaigns", "updated_at")
    op.drop_column("campaigns", "brief_snapshot")
    op.drop_column("campaigns", "search_query")
    op.drop_column("campaigns", "entry_point")
    op.drop_column("campaigns", "campaign_name")
