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
    UniqueConstraint,
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


class User(Base):
    """Registered user accounts for authentication and campaign ownership."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    timezone = Column(String, nullable=True, default="UTC")
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    brand_profile = relationship(
        "BrandProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notification_preference = relationship(
        "NotificationPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    integration_connections = relationship(
        "IntegrationConnection", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    subscription = relationship(
        "Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    saved_lists = relationship(
        "SavedList",
        back_populates="user",
        cascade="all, delete-orphan",
        overlaps="user",
    )


class BrandProfile(Base):
    """Onboarding answers describing the brand a user manages.

    One-to-one with :class:`User`; created/updated by the onboarding
    wizard (POST /api/onboarding) and used to calibrate match scoring
    defaults for that user's campaigns.
    """
    __tablename__ = "brand_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    brand_name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    country = Column(String, nullable=True)
    goals = Column(JSONB, nullable=True)
    platforms = Column(JSONB, nullable=True)
    monthly_budget = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="brand_profile")


class Campaign(Base):
    """Stores brand campaign metadata, lifecycle state, and scoring customizations."""
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    org_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    product = Column(String, nullable=False)
    niche = Column(String, nullable=False)
    goals = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    preferred_platforms = Column(JSONB, nullable=True)
    budget_range = Column(String, nullable=True)
    weights = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    campaign_name = Column(String(255), nullable=True)
    entry_point = Column(String(32), nullable=True, default="brief_form")
    search_query = Column(Text, nullable=True)
    brief_snapshot = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    brand = relationship("Brand", back_populates="campaigns")
    scores = relationship("InfluencerScore", back_populates="campaign", cascade="all, delete-orphan")
    crawl_sources = relationship("CrawlSource", back_populates="campaign", cascade="all, delete-orphan")
    brand_safety_flags = relationship("BrandSafetyFlag", back_populates="campaign", cascade="all, delete-orphan")
    saved_list_items = relationship("SavedListItem", back_populates="campaign")
    contracts = relationship("CampaignContract", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint(
            "created_by",
            "product",
            "niche",
            name="uq_campaigns_owner_product_niche",
        ),
    )


class Influencer(Base):
    """Canonical details of a resolved influencer profile."""
    __tablename__ = "influencers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(String, nullable=False)
    platforms = Column(JSONB, nullable=False)
    credentials = Column(JSONB, nullable=True)
    mentions = Column(JSONB, nullable=True)
    primary_platform = Column(String(32), nullable=True)
    primary_handle = Column(String(255), nullable=True)
    follower_count = Column(Integer, nullable=True)
    engagement_rate = Column(Float, nullable=True)
    avg_views = Column(Integer, nullable=True)
    primary_category = Column(String(128), nullable=True)
    primary_location = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    scores = relationship("InfluencerScore", back_populates="influencer", cascade="all, delete-orphan")
    crawl_sources = relationship("CrawlSource", back_populates="influencer")
    crawl_source_links = relationship(
        "CrawlSourceInfluencer", back_populates="influencer", cascade="all, delete-orphan"
    )
    brand_safety_flags = relationship("BrandSafetyFlag", back_populates="influencer", cascade="all, delete-orphan")
    verifications = relationship("CredentialVerification", back_populates="influencer", cascade="all, delete-orphan")
    saved_list_items = relationship("SavedListItem", back_populates="influencer", cascade="all, delete-orphan")
    campaign_contracts = relationship(
        "CampaignContract", back_populates="influencer", cascade="all, delete-orphan"
    )


class InfluencerScore(Base):
    """Stores metrics, score explanations, and source provenance for a scoring run."""
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

    confidence_level = Column(String, nullable=False)
    data_source_count = Column(Integer, nullable=False, default=0)
    score_version = Column(String, nullable=False, default="v1.0")
    signal_scores = Column(JSONB, nullable=True)
    risk_category = Column(String, nullable=True)
    detection_category = Column(String, nullable=True)
    positive_reasons = Column(JSONB, nullable=True)
    negative_reasons = Column(JSONB, nullable=True)
    source_provenance = Column(JSONB, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    influencer = relationship("Influencer", back_populates="scores")
    campaign = relationship("Campaign", back_populates="scores")


class CrawlSource(Base):
    """Tracks URLs discovered, fetched, parsed, and attributed during execution."""
    __tablename__ = "crawl_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=True)

    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    html = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="crawl_sources")
    influencer = relationship("Influencer", back_populates="crawl_sources")
    influencer_links = relationship(
        "CrawlSourceInfluencer", back_populates="crawl_source", cascade="all, delete-orphan"
    )


class CrawlSourceInfluencer(Base):
    """Durable attribution between a crawl source and one or more influencers."""
    __tablename__ = "crawl_source_influencers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crawl_source_id = Column(UUID(as_uuid=True), ForeignKey("crawl_sources.id"), nullable=False)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False)
    mention_id = Column(String, nullable=True)
    mention = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    crawl_source = relationship("CrawlSource", back_populates="influencer_links")
    influencer = relationship("Influencer", back_populates="crawl_source_links")

    __table_args__ = (
        UniqueConstraint("crawl_source_id", "influencer_id", "mention_id", name="uq_crawl_source_influencer_mention"),
    )


class BrandSafetyFlag(Base):
    """Specific brand safety concern flags discovered by LLM Pass 2."""
    __tablename__ = "brand_safety_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)

    source_url = Column(String, nullable=False)
    risk_type = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    influencer = relationship("Influencer", back_populates="brand_safety_flags")
    campaign = relationship("Campaign", back_populates="brand_safety_flags")


class CredentialVerification(Base):
    """Tracks verification credentials claimed by an influencer."""
    __tablename__ = "credential_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    influencer_id = Column(UUID(as_uuid=True), ForeignKey("influencers.id"), nullable=False)
    credential_type = Column(String, nullable=False)
    credential_value = Column(String, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    influencer = relationship("Influencer", back_populates="verifications")


Index("idx_influencer_scores_campaign", InfluencerScore.campaign_id)
Index("idx_influencer_scores_influencer", InfluencerScore.influencer_id)
Index(
    "idx_influencer_scores_campaign_final",
    InfluencerScore.campaign_id,
    InfluencerScore.final_score.desc(),
)
Index("idx_crawl_sources_campaign", CrawlSource.campaign_id)
Index("idx_crawl_sources_url", CrawlSource.url)
Index(
    "idx_crawl_sources_campaign_status",
    CrawlSource.campaign_id,
    CrawlSource.status,
)
Index("idx_crawl_source_influencers_source", CrawlSourceInfluencer.crawl_source_id)
Index("idx_crawl_source_influencers_influencer", CrawlSourceInfluencer.influencer_id)
Index("idx_brand_safety_influencer", BrandSafetyFlag.influencer_id)
Index("idx_brand_safety_campaign", BrandSafetyFlag.campaign_id)
Index("idx_credential_verifications_influencer", CredentialVerification.influencer_id)
Index("idx_campaigns_created_by", Campaign.created_by)
Index("idx_campaigns_entry_point", Campaign.entry_point)


class SavedList(Base):
    """User-curated collection of influencers.

    One row per user-named list (e.g. "Ramadan Campaign 2026").
    Soft enum ``status`` keeps the same vocabulary as the legacy
    frontend (``"active"`` / ``"draft"``) so existing UI components
    render without translation work.
    """
    __tablename__ = "saved_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active", server_default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    items = relationship(
        "SavedListItem", back_populates="list", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="saved_lists", overlaps="saved_lists")


class SavedListItem(Base):
    """Junction row connecting a :class:`SavedList` to an :class:`Influencer`.

    The ``source_campaign_id`` preserves the campaign the creator was
    added from so the same creator can appear in the same list under
    different campaigns without violating the unique constraint.
    ``match_score_snapshot`` freezes the score that justified the add.
    """
    __tablename__ = "saved_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(
        UUID(as_uuid=True), ForeignKey("saved_lists.id", ondelete="CASCADE"), nullable=False
    )
    influencer_id = Column(
        UUID(as_uuid=True), ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False
    )
    source_campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    match_score_snapshot = Column(Float, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    list = relationship("SavedList", back_populates="items")
    influencer = relationship("Influencer", back_populates="saved_list_items")
    campaign = relationship("Campaign", back_populates="saved_list_items")

    __table_args__ = (
        UniqueConstraint(
            "list_id",
            "influencer_id",
            "source_campaign_id",
            name="uq_saved_list_items_list_influencer_source",
        ),
    )


class CampaignContract(Base):
    """Outreach contract status linking a campaign to an influencer."""
    __tablename__ = "campaign_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    influencer_id = Column(
        UUID(as_uuid=True), ForeignKey("influencers.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String(32), nullable=False, default="contracted", server_default="contracted")
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="contracts")
    influencer = relationship("Influencer", back_populates="campaign_contracts")

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "influencer_id",
            name="uq_campaign_contracts_campaign_influencer",
        ),
    )


class NotificationPreference(Base):
    """Per-user notification toggles shown on the settings page.

    One-to-one with :class:`User`. The defaults match the values
    hardcoded in the legacy ``SettingsToggles`` component: shortlist
    ready & creator replied & product updates on, weekly digest off.
    """
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    shortlist_ready = Column(Boolean, nullable=False, default=True, server_default="true")
    creator_replied = Column(Boolean, nullable=False, default=True, server_default="true")
    weekly_digest = Column(Boolean, nullable=False, default=False, server_default="false")
    product_updates = Column(Boolean, nullable=False, default=True, server_default="true")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notification_preference")


class IntegrationConnection(Base):
    """Stub OAuth connection state for one provider (slack, hubspot, ...).

    A real implementation would store access/refresh tokens here; we
    just flip a boolean to drive the UI. Unique on
    ``(user_id, provider)`` so each user gets one row per provider.
    """
    __tablename__ = "integration_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider = Column(String, nullable=False)
    connected = Column(Boolean, nullable=False, default=False, server_default="false")
    connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="integration_connections")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_integration_connections_user_provider"),
    )


class ApiKey(Base):
    """API key issued to a user.

    ``key_prefix`` is the first 8 characters of the key, displayed in
    the UI so the user can recognise each key. ``key_hash`` is the
    full key hashed with the same bcrypt context used for passwords —
    we never store the plain key. The plain key is returned to the
    caller exactly once, in the create-response.
    """
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_keys")


class Subscription(Base):
    """Subscription plan for a user, synced from Stripe Billing.

    One-to-one with :class:`User`. ``plan`` is ``"starter"`` /
    ``"pro"`` / ``"scale"``. Paid Growth (``pro``) is provisioned via
    Stripe Checkout; downgrades and cancellations sync from webhooks.
    """
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan = Column(String, nullable=False, default="starter", server_default="starter")
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    billing_interval = Column(String, nullable=True)
    status = Column(String, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="subscription")
