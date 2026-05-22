from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.db import models
from app.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset", response_model=dict[str, str])
def reset_database(db: Session = Depends(get_db)) -> dict[str, str]:
    """Resets the development database by deleting all existing data in all tables."""
    log = logger.bind()
    try:
        log.info("Resetting demo database tables")
        
        # Delete dependent tables first to respect foreign key constraints
        db.query(models.BrandSafetyFlag).delete()
        db.query(models.CredentialVerification).delete()
        db.query(models.InfluencerScore).delete()
        db.query(models.CrawlSource).delete()
        db.query(models.Influencer).delete()
        db.query(models.Campaign).delete()
        db.query(models.Brand).delete()
        
        db.commit()
        log.info("Demo database reset completed successfully")
        return {"status": "ok", "message": "Database reset completed successfully."}
    except Exception as e:
        db.rollback()
        log.error("Failed to reset database", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")


@router.post("/seed", response_model=dict[str, Any])
def seed_database(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Seeds the database with high-quality, realistic demo campaigns, influencers, and scores."""
    log = logger.bind()
    try:
        log.info("Seeding demo database")
        
        # 1. First, reset the DB to ensure fresh seeds
        reset_database(db)
        
        # 2. Seed a default Brand for multi-tenant verification
        brand_id = uuid.uuid4()
        demo_brand = models.Brand(
            id=brand_id,
            name="Acme Health & Tech Corp",
            api_key="sk_live_demo_acme_123456789",
            created_at=datetime.utcnow()
        )
        db.add(demo_brand)
        db.flush()  # Push to database to ensure key checks pass
        
        # 3. Campaign A: "BioGlow Collagen Peptide" (Health/Beauty Niche)
        campaign_a_id = uuid.uuid4()
        campaign_a = models.Campaign(
            id=campaign_a_id,
            brand_id=brand_id,
            product="BioGlow Collagen Peptide",
            niche="beauty_health",
            goals="Identify trusted medical professionals and beauty experts with credential-backed credibility to promote our clean, grass-fed collagen peptides.",
            target_audience="Health-conscious women, ages 25-50, searching for clinical dermatological skin care routines and anti-aging advice.",
            preferred_platforms=["instagram", "youtube"],
            budget_range="$10,000 - $25,000",
            weights={
                "relevance": 0.30,
                "credibility": 0.35,
                "engagement": 0.15,
                "sentiment": 0.10,
                "brand_safety": 0.10
            },
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(campaign_a)
        
        # 4. Campaign B: "Apex DeFi Protocol" (Fintech/Crypto Niche)
        campaign_b_id = uuid.uuid4()
        campaign_b = models.Campaign(
            id=campaign_b_id,
            brand_id=brand_id,
            product="Apex DeFi Protocol",
            niche="fintech",
            goals="Discover financial analysts, economists, and smart contract engineers who understand decentralized finance yields, smart contract security, and can present them safely without triggering regulatory warning flags.",
            target_audience="DeFi enthusiasts, retail yield farmers, crypto-native builders, ages 18-40.",
            preferred_platforms=["twitter", "youtube", "linkedin"],
            budget_range="$50,000 - $100,000",
            weights={
                "relevance": 0.25,
                "credibility": 0.30,
                "engagement": 0.15,
                "sentiment": 0.10,
                "brand_safety": 0.20
            },
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(campaign_b)

        db.flush()

        # --- Seed Influencers and scores for Campaign A ---
        # Influencer A1: Dr. Jessica Cho (Highly credible board dermatologist)
        inf_a1_id = uuid.uuid4()
        inf_a1 = models.Influencer(
            id=inf_a1_id,
            canonical_name="Dr. Jessica Cho",
            platforms={"instagram": "@drjessicacho", "youtube": "youtube.com/c/drjessicacho"},
            credentials=["MD, Dermatology", "Board Certified Dermatologist"],
            mentions=[
                {
                    "name": "Jessica Cho MD",
                    "source_url": "https://dermatologytoday.com/articles/jessica-cho",
                    "context": "Dr. Jessica Cho highlights the benefits of marine collagen peptides on skin elasticity and dermal collagen density."
                }
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(inf_a1)

        score_a1 = models.InfluencerScore(
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
            computed_at=datetime.utcnow()
        )
        db.add(score_a1)

        verif_a1_1 = models.CredentialVerification(
            id=uuid.uuid4(),
            influencer_id=inf_a1_id,
            credential_type="license",
            credential_value="Medical License #MD9827451",
            verified=True,
            verified_at=datetime.utcnow() - timedelta(days=5)
        )
        verif_a1_2 = models.CredentialVerification(
            id=uuid.uuid4(),
            influencer_id=inf_a1_id,
            credential_type="education",
            credential_value="Stanford Medical School, MD, Dermatology",
            verified=True,
            verified_at=datetime.utcnow() - timedelta(days=5)
        )
        db.add(verif_a1_1)
        db.add(verif_a1_2)

        # Influencer A2: Elena Rostova (Esthetician, moderate scores)
        inf_a2_id = uuid.uuid4()
        inf_a2 = models.Influencer(
            id=inf_a2_id,
            canonical_name="Elena Rostova",
            platforms={"instagram": "@elenarostovabeauty", "tiktok": "@elenabeauty"},
            credentials=["Certified Esthetician"],
            mentions=[
                {
                    "name": "Elena Rostova",
                    "source_url": "https://skincareinsider.net/interviews/elena-rostova",
                    "context": "Elena recommends incorporating collagen peptides early into nightly anti-aging routines."
                }
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(inf_a2)

        score_a2 = models.InfluencerScore(
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
            computed_at=datetime.utcnow()
        )
        db.add(score_a2)

        # Source URLs for Campaign A
        src_a1 = models.CrawlSource(
            id=uuid.uuid4(),
            campaign_id=campaign_a_id,
            influencer_id=inf_a1_id,
            url="https://dermatologytoday.com/articles/jessica-cho",
            title="Dermatology Today: Science-Backed Skin Health",
            content="Full interview with Dr. Jessica Cho on collagen synthesis...",
            relevance_score=94.5,
            status="scraped",
            fetched_at=datetime.utcnow() - timedelta(days=1)
        )
        src_a2 = models.CrawlSource(
            id=uuid.uuid4(),
            campaign_id=campaign_a_id,
            influencer_id=inf_a2_id,
            url="https://skincareinsider.net/interviews/elena-rostova",
            title="Skincare Insider - Nightly Routine Tips",
            content="Esthetician Elena Rostova discusses peptide treatments...",
            relevance_score=85.0,
            status="scraped",
            fetched_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(src_a1)
        db.add(src_a2)


        # --- Seed Influencers and scores for Campaign B ---
        # Influencer B1: Alex Mason (DeFi Analyst, CFA)
        inf_b1_id = uuid.uuid4()
        inf_b1 = models.Influencer(
            id=inf_b1_id,
            canonical_name="Alex Mason",
            platforms={"youtube": "youtube.com/c/alexmasonfinance", "twitter": "@alexmasoncfa"},
            credentials=["Chartered Financial Analyst (CFA)"],
            mentions=[
                {
                    "name": "Alex Mason",
                    "source_url": "https://blockworks.co/news/alex-mason-defi",
                    "context": "Alex Mason analyzes the liquidity mining incentives of the Apex protocol and finds yield sustainability parameters robust."
                }
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(inf_b1)

        score_b1 = models.InfluencerScore(
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
            computed_at=datetime.utcnow()
        )
        db.add(score_b1)

        verif_b1 = models.CredentialVerification(
            id=uuid.uuid4(),
            influencer_id=inf_b1_id,
            credential_type="certification",
            credential_value="Chartered Financial Analyst Charter #82715",
            verified=True,
            verified_at=datetime.utcnow() - timedelta(days=30)
        )
        db.add(verif_b1)

        # Influencer B2: Crypto King (Shill account, poor scores, brand safety issues)
        inf_b2_id = uuid.uuid4()
        inf_b2 = models.Influencer(
            id=inf_b2_id,
            canonical_name="Crypto King",
            platforms={"twitter": "@cryptoking_degen", "tiktok": "@cryptoking"},
            credentials=[],
            mentions=[
                {
                    "name": "Crypto King",
                    "source_url": "https://coinscamalert.com/post/cryptoking-promo",
                    "context": "Crypto King hyped high-leverage positions on unverified microcaps, violating basic brand safety principles."
                }
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(inf_b2)

        score_b2 = models.InfluencerScore(
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
            computed_at=datetime.utcnow()
        )
        db.add(score_b2)

        # Add safety flag for Crypto King
        safety_flag = models.BrandSafetyFlag(
            id=uuid.uuid4(),
            influencer_id=inf_b2_id,
            campaign_id=campaign_b_id,
            source_url="https://coinscamalert.com/post/cryptoking-promo",
            risk_type="scam",
            reason="Promoted microcap pump and dump schemes and high-leverage crypto derivative trading without disclosing sponsorship relationships.",
            created_at=datetime.utcnow()
        )
        db.add(safety_flag)

        # Source URLs for Campaign B
        src_b1 = models.CrawlSource(
            id=uuid.uuid4(),
            campaign_id=campaign_b_id,
            influencer_id=inf_b1_id,
            url="https://blockworks.co/news/alex-mason-defi",
            title="Blockworks: DeFi Yield Sustainability Metrics",
            content="Alex Mason's comprehensive review on DeFi yield structure...",
            relevance_score=89.5,
            status="scraped",
            fetched_at=datetime.utcnow() - timedelta(days=1)
        )
        src_b2 = models.CrawlSource(
            id=uuid.uuid4(),
            campaign_id=campaign_b_id,
            influencer_id=inf_b2_id,
            url="https://coinscamalert.com/post/cryptoking-promo",
            title="CoinScamAlert: Promoters Under Fire",
            content="Crypto King faces severe user complaints after promoting leveraged rugpulls...",
            relevance_score=70.0,
            status="scraped",
            fetched_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(src_b1)
        db.add(src_b2)

        db.commit()
        log.info("Demo database seeded successfully")
        
        return {
            "status": "ok",
            "brand_id": brand_id,
            "campaigns": {
                "BioGlow Collagen Peptide": campaign_a_id,
                "Apex DeFi Protocol": campaign_b_id
            },
            "influencers": {
                "Dr. Jessica Cho": inf_a1_id,
                "Elena Rostova": inf_a2_id,
                "Alex Mason": inf_b1_id,
                "Crypto King": inf_b2_id
            }
        }
    except Exception as e:
        db.rollback()
        log.error("Failed to seed database", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database seed failed: {str(e)}")
