"""add_influencer_campaign_embeddings

Add nullable JSONB ``embedding`` columns to ``influencers`` and
``campaigns`` for semantic relevance scoring (plan 06).  The column
stores an envelope of shape::

    {"source": "openrouter", "model": "...", "vector": [...]}

The ``source`` field is always ``"openrouter"``; the underlying vector
is either a real OpenRouter embedding (when the key is configured) or
a deterministic hash-derived stub vector (when it is not). The stub
vs live distinction is implicit in the vector values, not in the
``source`` field.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "p2q3r4s5t6u7"
down_revision: str | None = "o1p2q3r4s5t6"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("influencers", sa.Column("embedding", JSONB(), nullable=True))
    op.add_column("campaigns", sa.Column("embedding", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "embedding")
    op.drop_column("influencers", "embedding")
