"""Persist influencer identity merges."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, aliased

from backend.core.database import models

log = logging.getLogger(__name__)


def _repoint_influencer_fk(
    session: Session,
    model: type,
    *,
    merged_id: UUID,
    canonical_id: UUID,
    sibling_cols: tuple[str, ...],
) -> None:
    """Move ``model.influencer_id`` from ``merged_id`` to ``canonical_id``.

    ``model`` carries a unique constraint on ``(influencer_id, *sibling_cols)``,
    so a blind bulk UPDATE collides when the canonical row already links the same
    sibling values (e.g. the same crawl_source + mention). We first delete the
    merged rows that would duplicate an existing canonical row, then re-point the
    survivors. NULL sibling values compare as distinct — matching Postgres unique
    semantics — so they never collide and are always re-pointed.
    """
    canon = aliased(model)
    session.query(model).filter(
        model.influencer_id == merged_id,
        session.query(canon)
        .filter(
            canon.influencer_id == canonical_id,
            *[getattr(canon, col) == getattr(model, col) for col in sibling_cols],
        )
        .exists(),
    ).delete(synchronize_session=False)
    session.flush()
    session.query(model).filter(
        model.influencer_id == merged_id
    ).update({model.influencer_id: canonical_id}, synchronize_session=False)


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

    # (crawl_source_id, influencer_id, mention_id) is unique — drop merged links
    # that already exist for the canonical influencer before re-pointing.
    _repoint_influencer_fk(
        session,
        models.CrawlSourceInfluencer,
        merged_id=merged_id,
        canonical_id=canonical_id,
        sibling_cols=("crawl_source_id", "mention_id"),
    )
    session.query(models.CrawlSource).filter(
        models.CrawlSource.influencer_id == merged_id
    ).update({models.CrawlSource.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.PlatformProfile).filter(
        models.PlatformProfile.influencer_id == merged_id
    ).update({models.PlatformProfile.influencer_id: canonical_id}, synchronize_session=False)
    # Find campaigns where the canonical already has a current score — the merged
    # influencer's scores for those campaigns must be demoted first, or the bulk
    # UPDATE would create a second (campaign_id, canonical_id, is_current=True)
    # row and violate uq_influencer_scores_current.
    canonical_scored_campaigns = {
        row.campaign_id
        for row in session.query(models.InfluencerScore.campaign_id)
        .filter(
            models.InfluencerScore.influencer_id == canonical_id,
            models.InfluencerScore.is_current == True,  # noqa: E712
        )
        .all()
    }
    if canonical_scored_campaigns:
        session.query(models.InfluencerScore).filter(
            models.InfluencerScore.influencer_id == merged_id,
            models.InfluencerScore.campaign_id.in_(canonical_scored_campaigns),
        ).update({models.InfluencerScore.is_current: False}, synchronize_session=False)

    session.query(models.InfluencerScore).filter(
        models.InfluencerScore.influencer_id == merged_id
    ).update({models.InfluencerScore.influencer_id: canonical_id}, synchronize_session=False)
    session.query(models.BrandSafetyFlag).filter(
        models.BrandSafetyFlag.influencer_id == merged_id
    ).update({models.BrandSafetyFlag.influencer_id: canonical_id}, synchronize_session=False)
    # Both tables carry a unique constraint that includes influencer_id, so the
    # same delete-then-repoint dance avoids duplicate-key violations.
    _repoint_influencer_fk(
        session,
        models.SavedListItem,
        merged_id=merged_id,
        canonical_id=canonical_id,
        sibling_cols=("list_id", "source_campaign_id"),
    )
    _repoint_influencer_fk(
        session,
        models.CampaignContract,
        merged_id=merged_id,
        canonical_id=canonical_id,
        sibling_cols=("campaign_id",),
    )

    log.info(
        "identity merge persisted canonical=%s merged=%s confidence=%.2f",
        canonical_id,
        merged_id,
        confidence,
    )
    return merge_row
