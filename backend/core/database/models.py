from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.core.database.session import Base


class Brand(Base):
    """Multi-tenant support table representing a brand client."""
    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaigns = relationship("Campaign", back_populates="brand", cascade="all, delete-orphan")


class Campaign(Base):
    """Stores brand campaign metadata and scoring weight customizations."""
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    product = Column(String, nullable=False)
    niche = Column(String, nullable=False)  # Industry/niche
    goals = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    preferred_platforms = Column(JSONB, nullable=True)  # List of strings e.g. ["instagram", "youtube"]
    budget_range = Column(String, nullable=True)
    weights = Column(JSONB, nullable=True)  # custom weight distribution dict
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    brand = relationship("Brand", back_populates="campaigns")
    scores = relationship("InfluencerScore", back_populates="campaign", cascade="all, delete-orphan")
    crawl_sources = relationship("CrawlSource", back_populates="campaign", cascade="all, delete-orphan")
    brand_safety_flags = relationship("BrandSafetyFlag", back_populates="campaign", cascade="all, delete-orphan")


class Influencer(Base):
    """Canonical details of a resolved influencer profile."""
    __tablename__ = "influencers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(String, nullable=False)
    platforms = Column(JSONB, nullable=False)  # e.g. {"instagram": "@handle", "youtube": "youtube.com/channel"}
    credentials = Column(JSONB, nullable=True)  # list of credentials
    mentions = Column(JSONB, nullable=True)  # list of raw mentions mapping context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scores = relationship("InfluencerScore", back_populates="influencer", cascade="all, delete-orphan")
    crawl_sources = relationship("CrawlSource", back_populates="influencer")
    brand_safety_flags = relationship("BrandSafetyFlag", back_populates="influencer", cascade="all, delete-orphan")
    verifications = relationship("CredentialVerification", back_populates="influencer", cascade="all, delete-orphan")


class InfluencerScore(Base):
    """Stores metrics and sub-scores for a specific scoring run."""
    __tablename__ = "influencer_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)

    final_score = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=False)
    credibility_score = Column(Float, nullable=False)
    engagement_score = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    brand_safety_score = Column(Float, nullable=False)

    confidence_level = Column(String, nullable=False)  # High / Medium / Low
    data_source_count = Column(Integer, nullable=False, default=0)
    score_version = Column(String, nullable=False, default="v1.0")
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    influencer = relationship("Influencer", back_populates="scores")
    campaign = relationship("Campaign", back_populates="scores")


class CrawlSource(Base):
    """Tracks URLs discovered, fetched and parsed during execution."""
    __tablename__ = "crawl_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=True)

    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, scraped, failed
    error_message = Column(Text, nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="crawl_sources")
    influencer = relationship("Influencer", back_populates="crawl_sources")


class BrandSafetyFlag(Base):
    """Specific brand safety concern flags discovered by LLM Pass 2."""
    __tablename__ = "brand_safety_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)

    source_url = Column(String, nullable=False)
    risk_type = Column(String, nullable=False)  # hate_speech, misinformation, scam, toxic, undisclosed_sponsorships
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    influencer = relationship("Influencer", back_populates="brand_safety_flags")
    campaign = relationship("Campaign", back_populates="brand_safety_flags")


class CredentialVerification(Base):
    """Tracks verification credentials claimed by an influencer."""
    __tablename__ = "credential_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False)
    credential_type = Column(String, nullable=False)  # education, certification, license
    credential_value = Column(String, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    influencer = relationship("Influencer", back_populates="verifications")


# Indexes for efficient filtering and relational joins
Index("idx_influencer_scores_campaign", InfluencerScore.campaign_id)
Index("idx_influencer_scores_influencer", InfluencerScore.influencer_id)
Index("idx_crawl_sources_campaign", CrawlSource.campaign_id)
Index("idx_crawl_sources_url", CrawlSource.url)
Index("idx_brand_safety_influencer", BrandSafetyFlag.influencer_id)
Index("idx_brand_safety_campaign", BrandSafetyFlag.campaign_id)
Index("idx_credential_verifications_influencer", CredentialVerification.influencer_id)
