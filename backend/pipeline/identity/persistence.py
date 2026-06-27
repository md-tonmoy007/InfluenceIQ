"""Persist influencer identity merges."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.core.database import models

log = logging.getLogger(__name__)


def apply_merge(
    session: Session,
    *,
    campaign_id: UUID | None,
    canonical_id: UUID,
    merged_id: UUID,
    confidence: float,
    merge_strategy: str,
    reason: str,
) -> models.IdentityMerge | None:
    """Consolidate duplicate influencer rows into a canonical record."""
    if canonical_id == merged_id:
        return None

    canonical = session.get(models.Influencer, canonical_id)
    merged = session.get(models.Influencer, merged_id)
    if canonical is None or merged is None:
        return None

    existing = (
        session.query(models.IdentityMerge)
        .filter(
            models.IdentityMerge.canonical_influencer_id == canonical_id,
            models.IdentityMerge.merged_influencer_id == merged_id,
        )
        .first()
    )
    if existing:
        return existing

    merge_row = models.IdentityMerge(
        id=uuid4(),
        campaign_id=campaign_id,
        canonical_influencer_id=canonical_id,
        merged_influencer_id=merged_id,
        confidence=confidence,
        merge_strategy=merge_strategy,
        reason=reason,
        merged_at=datetime.now(UTC),
    )
    session.add(merge_row)

    canonical.platforms = {**(merged.platforms or {}), **(canonical.platforms or {})}
    canonical.credentials = list(dict.fromkeys([*(canonical.credentials or []), *(merged.credentials or [])]))
    canonical.mentions = list((canonical.mentions or []) + (merged.mentions or []))
    canonical.is_canonical = True
    merged.merged_into_id = canonical_id
    merged.is_canonical = False

    session.query(models.CrawlSourceInfluencer).filter(
        models.CrawlSourceInfluencer.influencer_id == merged_id
    ).update({models.CrawlSourceInfluencer.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.CrawlSource).filter(
        models.CrawlSource.influencer_id == merged_id
    ).update({models.CrawlSource.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.PlatformProfile).filter(
        models.PlatformProfile.influencer_id == merged_id
    ).update({models.PlatformProfile.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.InfluencerScore).filter(
        models.InfluencerScore.influencer_id == merged_id
    ).update({models.InfluencerScore.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.BrandSafetyFlag).filter(
        models.BrandSafetyFlag.influencer_id == merged_id
    ).update({models.BrandSafetyFlag.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.SavedListItem).filter(
        models.SavedListItem.influencer_id == merged_id
    ).update({models.SavedListItem.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.CampaignContract).filter(
        models.CampaignContract.influencer_id == merged_id
    ).update({models.CampaignContract.influencer_id: canonical_id}, synchronize_session=False)

    log.info(
        "identity merge persisted canonical=%s merged=%s confidence=%.2f",
        canonical_id,
        merged_id,
        confidence,
    )
    return merge_row
