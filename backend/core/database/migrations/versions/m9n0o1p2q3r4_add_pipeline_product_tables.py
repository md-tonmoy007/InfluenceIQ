"""add_pipeline_product_tables

Platform enrichment, score audit, identity merges, credential/safety audit,
and deep analysis tables.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m9n0o1p2q3r4"
down_revision: str | None = "l8m9n0o1p2q3"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("influencers", sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("influencers", sa.Column("is_canonical", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("influencers", sa.Column("identity_confidence", sa.Float(), nullable=True))
    op.create_foreign_key(
        "fk_influencers_merged_into",
        "influencers",
        "influencers",
        ["merged_into_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("influencer_scores", sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("influencer_scores", sa.Column("run_trigger", sa.String(length=32), nullable=True))
    op.add_column("influencer_scores", sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("influencer_scores", sa.Column("scoring_weights", postgresql.JSONB(), nullable=True))
    op.add_column("influencer_scores", sa.Column("grade", sa.String(length=8), nullable=True))
    op.add_column("influencer_scores", sa.Column("trust_caps", postgresql.JSONB(), nullable=True))
    op.add_column("influencer_scores", sa.Column("model_versions", postgresql.JSONB(), nullable=True))
    op.add_column("influencer_scores", sa.Column("explanation_payload", postgresql.JSONB(), nullable=True))
    op.create_foreign_key(
        "fk_influencer_scores_superseded_by",
        "influencer_scores",
        "influencer_scores",
        ["superseded_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_influencer_scores_current",
        "influencer_scores",
        ["campaign_id", "influencer_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    op.add_column("brand_safety_flags", sa.Column("severity", sa.String(length=16), nullable=True))
    op.add_column("brand_safety_flags", sa.Column("detection_method", sa.String(length=32), nullable=True))
    op.add_column("brand_safety_flags", sa.Column("matched_keyword", sa.String(length=255), nullable=True))
    op.add_column("brand_safety_flags", sa.Column("context_snippet", sa.Text(), nullable=True))
    op.add_column("brand_safety_flags", sa.Column("model_provider", sa.String(length=64), nullable=True))
    op.add_column("brand_safety_flags", sa.Column("model_name", sa.String(length=128), nullable=True))
    op.add_column("brand_safety_flags", sa.Column("requires_llm_review", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("brand_safety_flags", sa.Column("score_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_brand_safety_flags_score_run",
        "brand_safety_flags",
        "influencer_scores",
        ["score_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("credential_verifications", sa.Column("source_url", sa.String(length=2048), nullable=True))
    op.add_column("credential_verifications", sa.Column("crawl_source_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("credential_verifications", sa.Column("extracted_claim", sa.Text(), nullable=True))
    op.add_column("credential_verifications", sa.Column("verifier", sa.String(length=64), nullable=True))
    op.add_column("credential_verifications", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("credential_verifications", sa.Column("review_state", sa.String(length=32), nullable=True))
    op.add_column("credential_verifications", sa.Column("evidence", postgresql.JSONB(), nullable=True))
    op.create_foreign_key(
        "fk_credential_verifications_crawl_source",
        "credential_verifications",
        "crawl_sources",
        ["crawl_source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "platform_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("influencer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("platform_account_id", sa.String(length=255), nullable=True),
        sa.Column("handle", sa.String(length=255), nullable=True),
        sa.Column("profile_url", sa.String(length=2048), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("following", sa.Integer(), nullable=True),
        sa.Column("avg_engagement", sa.Integer(), nullable=True),
        sa.Column("engagement_rate", sa.Float(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("fetch_provider", sa.String(length=64), nullable=True),
        sa.Column("fetch_status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("platform", "profile_url", name="uq_platform_profiles_platform_url"),
    )
    op.create_index("idx_platform_profiles_influencer", "platform_profiles", ["influencer_id"])

    op.create_table(
        "platform_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("platform_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("platform_post_id", sa.String(length=255), nullable=False),
        sa.Column("post_url", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=True),
        sa.Column("fetch_provider", sa.String(length=64), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("platform_profile_id", "platform_post_id", name="uq_platform_posts_profile_post"),
    )

    op.create_table(
        "platform_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("platform_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_comment_id", sa.String(length=255), nullable=True),
        sa.Column("author_handle_hash", sa.String(length=128), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_platform_comments_post", "platform_comments", ["platform_post_id"])

    op.create_table(
        "candidate_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("influencer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("platform_fetch_watermark", sa.DateTime(), nullable=True),
        sa.Column("built_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "identity_merges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("canonical_influencer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merged_influencer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("merge_strategy", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("merged_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("canonical_influencer_id", "merged_influencer_id", name="uq_identity_merges_pair"),
    )

    op.create_table(
        "deep_analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("influencer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("requested_comment_target", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column("collected_comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_coverage", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "deep_analysis_post_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deep_analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("fake_comment_risk", sa.Float(), nullable=True),
        sa.Column("toxicity_score", sa.Float(), nullable=True),
        sa.Column("engagement_quality", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "deep_analysis_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deep_analysis_runs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("overall_grade", sa.String(length=8), nullable=True),
        sa.Column("audience_sentiment", sa.Float(), nullable=True),
        sa.Column("fake_engagement_risk", sa.Float(), nullable=True),
        sa.Column("brand_safety_summary", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("report_payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("deep_analysis_reports")
    op.drop_table("deep_analysis_post_results")
    op.drop_table("deep_analysis_runs")
    op.drop_table("identity_merges")
    op.drop_table("candidate_snapshots")
    op.drop_table("platform_comments")
    op.drop_table("platform_posts")
    op.drop_table("platform_profiles")
    op.drop_constraint("fk_credential_verifications_crawl_source", "credential_verifications", type_="foreignkey")
    op.drop_column("credential_verifications", "evidence")
    op.drop_column("credential_verifications", "review_state")
    op.drop_column("credential_verifications", "confidence")
    op.drop_column("credential_verifications", "verifier")
    op.drop_column("credential_verifications", "extracted_claim")
    op.drop_column("credential_verifications", "crawl_source_id")
    op.drop_column("credential_verifications", "source_url")
    op.drop_constraint("fk_brand_safety_flags_score_run", "brand_safety_flags", type_="foreignkey")
    op.drop_column("brand_safety_flags", "score_run_id")
    op.drop_column("brand_safety_flags", "requires_llm_review")
    op.drop_column("brand_safety_flags", "model_name")
    op.drop_column("brand_safety_flags", "model_provider")
    op.drop_column("brand_safety_flags", "context_snippet")
    op.drop_column("brand_safety_flags", "matched_keyword")
    op.drop_column("brand_safety_flags", "detection_method")
    op.drop_column("brand_safety_flags", "severity")
    op.drop_index("uq_influencer_scores_current", table_name="influencer_scores")
    op.drop_constraint("fk_influencer_scores_superseded_by", "influencer_scores", type_="foreignkey")
    op.drop_column("influencer_scores", "explanation_payload")
    op.drop_column("influencer_scores", "model_versions")
    op.drop_column("influencer_scores", "trust_caps")
    op.drop_column("influencer_scores", "grade")
    op.drop_column("influencer_scores", "scoring_weights")
    op.drop_column("influencer_scores", "superseded_by")
    op.drop_column("influencer_scores", "run_trigger")
    op.drop_column("influencer_scores", "is_current")
    op.drop_constraint("fk_influencers_merged_into", "influencers", type_="foreignkey")
    op.drop_column("influencers", "identity_confidence")
    op.drop_column("influencers", "is_canonical")
    op.drop_column("influencers", "merged_into_id")
