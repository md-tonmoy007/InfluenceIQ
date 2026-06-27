from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend.core.database import models


def clear_campaign_run_artifacts(db: Session, campaign_id: UUID) -> None:
    """Delete pipeline output for one campaign run. Keeps contracts and global influencers."""
    db.query(models.BrandSafetyFlag).filter(
        models.BrandSafetyFlag.campaign_id == campaign_id
    ).delete(synchronize_session=False)
    db.query(models.DeepAnalysisRun).filter(
        models.DeepAnalysisRun.campaign_id == campaign_id
    ).delete(synchronize_session=False)
    db.query(models.CandidateSnapshot).filter(
        models.CandidateSnapshot.campaign_id == campaign_id
    ).delete(synchronize_session=False)
    db.query(models.InfluencerScore).filter(
        models.InfluencerScore.campaign_id == campaign_id
    ).delete(synchronize_session=False)
    db.query(models.CrawlSource).filter(
        models.CrawlSource.campaign_id == campaign_id
    ).delete(synchronize_session=False)


def reset_campaign_lifecycle(db_campaign: models.Campaign, *, to_draft: bool) -> None:
    """Reset campaign lifecycle fields after clearing run artifacts."""
    if to_draft:
        db_campaign.status = "draft"
        db_campaign.started_at = None
    else:
        db_campaign.status = "running"
        db_campaign.started_at = datetime.now(UTC)
    db_campaign.completed_at = None
    db_campaign.failed_at = None
    db_campaign.failure_reason = None
    db_campaign.updated_at = datetime.now(UTC)


__all__ = ["clear_campaign_run_artifacts", "reset_campaign_lifecycle"]
