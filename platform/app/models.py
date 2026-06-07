from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def _json_type():
    return JSONB().with_variant(JSON(), "sqlite")


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand: Mapped[str] = mapped_column(String(255), default="")
    product: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(255), default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(_json_type(), default=dict)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    influencers: Mapped[list["InfluencerResult"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class InfluencerResult(Base):
    __tablename__ = "campaign_influencers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    influencer_id: Mapped[str] = mapped_column(String(64), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.campaign_id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    handle: Mapped[str] = mapped_column(String(255), default="")
    platform: Mapped[str] = mapped_column(String(64), default="unknown")
    followers: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    trust_grade: Mapped[str] = mapped_column(String(8), default="D")
    rate: Mapped[str] = mapped_column(String(64), default="TBD")
    brand_safety_flags: Mapped[list[str]] = mapped_column(_json_type(), default=list)
    citations: Mapped[list[str]] = mapped_column(_json_type(), default=list)
    sub_scores: Mapped[dict] = mapped_column(_json_type(), default=dict)
    score_payload: Mapped[dict] = mapped_column(_json_type(), default=dict)
    source_payload: Mapped[dict] = mapped_column(_json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    campaign: Mapped[Campaign] = relationship(back_populates="influencers")
