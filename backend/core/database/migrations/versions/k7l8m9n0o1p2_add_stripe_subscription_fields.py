"""add_stripe_subscription_fields

Adds Stripe Billing columns to ``subscriptions`` for checkout, portal,
and webhook sync.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "k7l8m9n0o1p2"
down_revision: str | None = "j6k7l8m9n0o1"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("subscriptions", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.add_column("subscriptions", sa.Column("billing_interval", sa.String(), nullable=True))
    op.add_column("subscriptions", sa.Column("status", sa.String(), nullable=True))
    op.add_column("subscriptions", sa.Column("trial_end", sa.DateTime(), nullable=True))
    op.add_column("subscriptions", sa.Column("current_period_end", sa.DateTime(), nullable=True))
    op.create_index(
        "idx_subscriptions_stripe_customer_id",
        "subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_subscriptions_stripe_subscription_id", "subscriptions", type_="unique")
    op.drop_index("idx_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_column("subscriptions", "current_period_end")
    op.drop_column("subscriptions", "trial_end")
    op.drop_column("subscriptions", "status")
    op.drop_column("subscriptions", "billing_interval")
    op.drop_column("subscriptions", "stripe_subscription_id")
    op.drop_column("subscriptions", "stripe_customer_id")
