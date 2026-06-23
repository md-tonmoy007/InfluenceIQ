"""add_settings_support

Adds the backend tables and columns that back the /settings page
(profile, brand, plan & billing, notifications, API & integrations,
danger zone):

* ``users`` gains ``role`` (free-text, nullable), ``timezone``
  (nullable, defaults to ``"UTC"`` for new rows), and ``deleted_at``
  (nullable timestamp used as a soft-delete marker — see
  ``backend.core.auth.get_current_user`` which filters on
  ``deleted_at IS NULL``).
* ``notification_preferences`` — one row per user, holds the four
  booleans the Notifications card toggles.
* ``integration_connections`` — one row per (user, provider) where
  ``provider`` is a small enum-like string (``"slack"`` / ``"hubspot"``).
  The "Connect" buttons flip ``connected``; no real OAuth is wired.
* ``api_keys`` — store ``key_prefix`` (first 8 chars, shown in the UI)
  and ``key_hash`` (full key hashed with the same bcrypt context as
  passwords). The full key is returned to the user exactly once at
  creation time. Revoked keys keep their row with ``revoked_at`` set.
* ``subscriptions`` — one row per user with a single ``plan`` string
  (default ``"starter"``). No payment fields — billing is stubbed.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-06-22 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i5j6k7l8m9n0"
down_revision: str | None = "h4i5j6k7l8m9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users: profile extension columns
    # ------------------------------------------------------------------
    op.add_column("users", sa.Column("role", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("timezone", sa.String(), nullable=True, server_default="UTC"),
    )
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # ------------------------------------------------------------------
    # notification_preferences
    # ------------------------------------------------------------------
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shortlist_ready", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("creator_replied", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("weekly_digest", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("product_updates", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )

    # ------------------------------------------------------------------
    # integration_connections
    # ------------------------------------------------------------------
    op.create_table(
        "integration_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "provider", name="uq_integration_connections_user_provider"
        ),
    )

    # ------------------------------------------------------------------
    # api_keys
    # ------------------------------------------------------------------
    op.create_table(
        "api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_api_keys_user", "api_keys", ["user_id"], unique=False)

    # ------------------------------------------------------------------
    # subscriptions
    # ------------------------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(), nullable=False, server_default="starter"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
    )


def downgrade() -> None:
    op.drop_table("subscriptions")

    op.drop_index("idx_api_keys_user", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_table("integration_connections")
    op.drop_table("notification_preferences")

    op.drop_column("users", "deleted_at")
    op.drop_column("users", "timezone")
    op.drop_column("users", "role")
