from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.orm import Session

from backend.core.database import models

logger = structlog.get_logger()


def reset_database(db: Session) -> None:
    """Delete all demo data, respecting foreign key order."""
    log = logger.bind()
    log.info("Resetting demo database tables")

    db.query(models.BrandSafetyFlag).delete()
    db.query(models.CredentialVerification).delete()
    db.query(models.InfluencerScore).delete()
    db.query(models.CrawlSourceInfluencer).delete()
    db.query(models.CrawlSource).delete()
    db.query(models.Influencer).delete()
    db.query(models.Campaign).delete()
    db.query(models.Brand).delete()
    db.commit()
    log.info("Demo database reset completed successfully")


def seed_database(db: Session) -> dict[str, Any]:
    """Seed realistic demo campaigns, influencers, and scores."""
    log = logger.bind()
    log.info("Seeding demo database")

    reset_database(db)

    brand_id = uuid.uuid4()
    demo_brand = models.Brand(
        id=brand_id,
        name="Acme Health & Tech Corp",
        api_key="sk_live_demo_acme_123456789",
        created_at=datetime.utcnow(),
    )
    db.add(demo_brand)
    db.flush()

    campaign_a_id = uuid.uuid4()
    campaign_a = models.Campaign(
        id=campaign_a_id,
        brand_id=brand_id,
        product="BioGlow Collagen Peptide",
        niche="beauty_health",
        goals=(
            "Identify trusted medical professionals and beauty experts with "
            "credential-backed credibility to promote our clean, grass-fed collagen peptides."
        ),
        target_audience=(
            "Health-conscious women, ages 25-50, searching for clinical dermatological "
            "skin care routines and anti-aging advice."
        ),
        preferred_platforms=["instagram", "youtube"],
        budget_range="$10,000 - $25,000",
        weights={
            "relevance": 0.30,
            "credibility": 0.35,
            "engagement": 0.15,
            "sentiment": 0.10,
            "brand_safety": 0.10,
        },
        status="completed",
        started_at=datetime.utcnow() - timedelta(days=2, hours=3),
        completed_at=datetime.utcnow() - timedelta(days=2),
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    db.add(campaign_a)

    campaign_b_id = uuid.uuid4()
    campaign_b = models.Campaign(
        id=campaign_b_id,
        brand_id=brand_id,
        product="Apex DeFi Protocol",
        niche="fintech",
        goals=(
            "Discover financial analysts, economists, and smart contract engineers who "
            "understand decentralized finance yields, smart contract security, and can "
            "present them safely without triggering regulatory warning flags."
        ),
        target_audience="DeFi enthusiasts, retail yield farmers, crypto-native builders, ages 18-40.",
        preferred_platforms=["twitter", "youtube", "linkedin"],
        budget_range="$50,000 - $100,000",
        weights={
            "relevance": 0.25,
            "credibility": 0.30,
            "engagement": 0.15,
            "sentiment": 0.10,
            "brand_safety": 0.20,
        },
        status="partial",
        started_at=datetime.utcnow() - timedelta(days=1, hours=6),
        completed_at=datetime.utcnow() - timedelta(days=1),
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add(campaign_b)
    db.flush()

    inf_a1_id = uuid.uuid4()
    inf_a1 = models.Influencer(
        id=inf_a1_id,
        canonical_name="Dr. Jessica Cho",
        platforms={"instagram": "@drjessicacho", "youtube": "youtube.com/c/drjessicacho"},
        credentials=["MD, Dermatology", "Board Certified Dermatologist"],
        mentions=[{
            "name": "Jessica Cho MD",
            "source_url": "https://dermatologytoday.com/articles/jessica-cho",
            "context": (
                "Dr. Jessica Cho highlights the benefits of marine collagen peptides on "
                "skin elasticity and dermal collagen density."
            ),
        }],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(inf_a1)
    db.add(models.InfluencerScore(
        id=uuid.uuid4(),
        influencer_id=inf_a1_id,
        campaign_id=campaign_a_id,
        final_score=92.5,
        relevance_score=94.0,
        credibility_score=96.0,
        engagement_score=88.0,
        sentiment_score=92.0,
        brand_safety_score=93.0,
        confidence_level="High",
        data_source_count=8,
        score_version="v1.0",
        computed_at=datetime.utcnow(),
    ))
    db.add(models.CredentialVerification(
        id=uuid.uuid4(),
        influencer_id=inf_a1_id,
        credential_type="license",
        credential_value="Medical License #MD9827451",
        verified=True,
        verified_at=datetime.utcnow() - timedelta(days=5),
    ))
    db.add(models.CredentialVerification(
        id=uuid.uuid4(),
        influencer_id=inf_a1_id,
        credential_type="education",
        credential_value="Stanford Medical School, MD, Dermatology",
        verified=True,
        verified_at=datetime.utcnow() - timedelta(days=5),
    ))

    inf_a2_id = uuid.uuid4()
    db.add(models.Influencer(
        id=inf_a2_id,
        canonical_name="Elena Rostova",
        platforms={"instagram": "@elenarostovabeauty", "tiktok": "@elenabeauty"},
        credentials=["Certified Esthetician"],
        mentions=[{
            "name": "Elena Rostova",
            "source_url": "https://skincareinsider.net/interviews/elena-rostova",
            "context": "Elena recommends incorporating collagen peptides early into nightly anti-aging routines.",
        }],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    db.add(models.InfluencerScore(
        id=uuid.uuid4(),
        influencer_id=inf_a2_id,
        campaign_id=campaign_a_id,
        final_score=83.2,
        relevance_score=85.0,
        credibility_score=81.0,
        engagement_score=89.0,
        sentiment_score=82.0,
        brand_safety_score=80.0,
        confidence_level="High",
        data_source_count=5,
        score_version="v1.0",
        computed_at=datetime.utcnow(),
    ))
    db.add(models.CrawlSource(
        id=uuid.uuid4(),
        campaign_id=campaign_a_id,
        influencer_id=inf_a1_id,
        url="https://dermatologytoday.com/articles/jessica-cho",
        title="Dermatology Today: Science-Backed Skin Health",
        content="Full interview with Dr. Jessica Cho on collagen synthesis...",
        relevance_score=94.5,
        status="scraped",
        fetched_at=datetime.utcnow() - timedelta(days=1),
    ))
    db.add(models.CrawlSource(
        id=uuid.uuid4(),
        campaign_id=campaign_a_id,
        influencer_id=inf_a2_id,
        url="https://skincareinsider.net/interviews/elena-rostova",
        title="Skincare Insider - Nightly Routine Tips",
        content="Esthetician Elena Rostova discusses peptide treatments...",
        relevance_score=85.0,
        status="scraped",
        fetched_at=datetime.utcnow() - timedelta(days=1),
    ))

    inf_b1_id = uuid.uuid4()
    db.add(models.Influencer(
        id=inf_b1_id,
        canonical_name="Alex Mason",
        platforms={"youtube": "youtube.com/c/alexmasonfinance", "twitter": "@alexmasoncfa"},
        credentials=["Chartered Financial Analyst (CFA)"],
        mentions=[{
            "name": "Alex Mason",
            "source_url": "https://blockworks.co/news/alex-mason-defi",
            "context": (
                "Alex Mason analyzes the liquidity mining incentives of the Apex protocol "
                "and finds yield sustainability parameters robust."
            ),
        }],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    db.add(models.InfluencerScore(
        id=uuid.uuid4(),
        influencer_id=inf_b1_id,
        campaign_id=campaign_b_id,
        final_score=86.4,
        relevance_score=90.0,
        credibility_score=85.0,
        engagement_score=92.0,
        sentiment_score=78.0,
        brand_safety_score=85.0,
        confidence_level="Medium",
        data_source_count=6,
        score_version="v1.0",
        computed_at=datetime.utcnow(),
    ))
    db.add(models.CredentialVerification(
        id=uuid.uuid4(),
        influencer_id=inf_b1_id,
        credential_type="certification",
        credential_value="Chartered Financial Analyst Charter #82715",
        verified=True,
        verified_at=datetime.utcnow() - timedelta(days=30),
    ))

    inf_b2_id = uuid.uuid4()
    db.add(models.Influencer(
        id=inf_b2_id,
        canonical_name="Crypto King",
        platforms={"twitter": "@cryptoking_degen", "tiktok": "@cryptoking"},
        credentials=[],
        mentions=[{
            "name": "Crypto King",
            "source_url": "https://coinscamalert.com/post/cryptoking-promo",
            "context": (
                "Crypto King hyped high-leverage positions on unverified microcaps, "
                "violating basic brand safety principles."
            ),
        }],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    db.add(models.InfluencerScore(
        id=uuid.uuid4(),
        influencer_id=inf_b2_id,
        campaign_id=campaign_b_id,
        final_score=58.0,
        relevance_score=80.0,
        credibility_score=45.0,
        engagement_score=95.0,
        sentiment_score=55.0,
        brand_safety_score=30.0,
        confidence_level="Low",
        data_source_count=3,
        score_version="v1.0",
        computed_at=datetime.utcnow(),
    ))
    db.add(models.BrandSafetyFlag(
        id=uuid.uuid4(),
        influencer_id=inf_b2_id,
        campaign_id=campaign_b_id,
        source_url="https://coinscamalert.com/post/cryptoking-promo",
        risk_type="scam",
        reason=(
            "Promoted microcap pump and dump schemes and high-leverage crypto derivative "
            "trading without disclosing sponsorship relationships."
        ),
        created_at=datetime.utcnow(),
    ))
    db.add(models.CrawlSource(
        id=uuid.uuid4(),
        campaign_id=campaign_b_id,
        influencer_id=inf_b1_id,
        url="https://blockworks.co/news/alex-mason-defi",
        title="Blockworks: DeFi Yield Sustainability Metrics",
        content="Alex Mason's comprehensive review on DeFi yield structure...",
        relevance_score=89.5,
        status="scraped",
        fetched_at=datetime.utcnow() - timedelta(days=1),
    ))
    db.add(models.CrawlSource(
        id=uuid.uuid4(),
        campaign_id=campaign_b_id,
        influencer_id=inf_b2_id,
        url="https://coinscamalert.com/post/cryptoking-promo",
        title="CoinScamAlert: Promoters Under Fire",
        content="Crypto King faces severe user complaints after promoting leveraged rugpulls...",
        relevance_score=70.0,
        status="scraped",
        fetched_at=datetime.utcnow() - timedelta(days=1),
    ))

    db.commit()
    log.info("Demo database seeded successfully")

    return {
        "status": "ok",
        "brand_id": brand_id,
        "campaigns": {
            "BioGlow Collagen Peptide": campaign_a_id,
            "Apex DeFi Protocol": campaign_b_id,
        },
        "influencers": {
            "Dr. Jessica Cho": inf_a1_id,
            "Elena Rostova": inf_a2_id,
            "Alex Mason": inf_b1_id,
            "Crypto King": inf_b2_id,
        },
    }
