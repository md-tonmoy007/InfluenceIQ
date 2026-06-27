"""Deep analysis Celery tasks."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.core.celery.app import celery_app
from backend.core.database import models
from backend.pipeline.analysis.engagement_quality import engagement_quality_score
from backend.pipeline.analysis.fake_comment import score_fake_comments
from backend.pipeline.analysis.sentiment import analyze_sentiment
from backend.pipeline.candidate.builder import build_influencer_candidate
from backend.pipeline.content.enrichment import enrich_influencer_platforms
from backend.pipeline.tasks._common import db_session, publish_event

log = logging.getLogger(__name__)


@celery_app.task(name="backend.pipeline.tasks.deep.deep_analyze", bind=True, max_retries=1)
def deep_analyze(
    self,
    campaign_id: str,
    influencer_id: str,
    run_id: str,
    *,
    comment_target: int = 2000,
) -> dict:
    """Collect comment corpus and build a deep analysis report."""
    log.info("deep_analyze campaign_id=%s influencer_id=%s run_id=%s", campaign_id, influencer_id, run_id)
    try:
        campaign_uuid = UUID(campaign_id)
        influencer_uuid = UUID(influencer_id)
        run_uuid = UUID(run_id)
    except (TypeError, ValueError):
        return {"status": "invalid_id"}

    publish_event(campaign_id, "deep_analysis.started", run_id=run_id, influencer_id=influencer_id)

    with db_session() as session:
        run = session.get(models.DeepAnalysisRun, run_uuid)
        if run is None:
            return {"status": "missing_run"}
        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.requested_comment_target = comment_target

        crawl_sources = (
            session.query(models.CrawlSource)
            .join(models.CrawlSourceInfluencer)
            .filter(
                models.CrawlSource.campaign_id == campaign_uuid,
                models.CrawlSourceInfluencer.influencer_id == influencer_uuid,
            )
            .all()
        )
        enrichment = enrich_influencer_platforms(session, influencer_uuid, crawl_sources=crawl_sources)
        candidate = build_influencer_candidate(
            session,
            influencer_uuid,
            campaign_uuid,
            comment_limit=comment_target,
        )
        comments = candidate.get("comments") or []
        run.collected_comment_count = len(comments)
        run.provider_coverage = enrichment.get("coverage", {})

        posts = (
            session.query(models.PlatformPost)
            .join(models.PlatformProfile)
            .filter(models.PlatformProfile.influencer_id == influencer_uuid)
            .order_by(models.PlatformPost.published_at.desc().nullslast())
            .limit(20)
            .all()
        )

        post_results: list[dict] = []
        sentiment_scores: list[float] = []
        fake_risks: list[float] = []
        engagement_scores: list[float] = []

        for post in posts:
            post_comments = [
                row.text
                for row in session.query(models.PlatformComment)
                .filter(models.PlatformComment.platform_post_id == post.id)
                .limit(200)
                .all()
                if row.text
            ]
            if not post_comments:
                continue
            sentiment = analyze_sentiment(post_comments)
            fake = score_fake_comments(post_comments)
            engagement = engagement_quality_score(
                {
                    "comments": post_comments,
                    "followers": candidate.get("followers", 0),
                    "average_engagement": candidate.get("average_engagement", 0),
                },
                fake_comment_risk=float(fake.get("fake_comment_risk", 0)),
            )
            sentiment_value = float(sentiment.get("sentiment_score", 50.0))
            fake_value = float(fake.get("fake_comment_risk", 0.0))
            engagement_value = float(engagement.get("engagement_quality_score", 50.0))
            sentiment_scores.append(sentiment_value)
            fake_risks.append(fake_value)
            engagement_scores.append(engagement_value)
            result_row = models.DeepAnalysisPostResult(
                id=uuid4(),
                run_id=run_uuid,
                platform_post_id=post.id,
                sentiment_score=sentiment_value,
                fake_comment_risk=fake_value,
                engagement_quality=engagement_value,
                summary=f"Analyzed {len(post_comments)} comments on {post.title or post.caption or post.post_url}",
                evidence={
                    "comment_count": len(post_comments),
                    "view_count": post.view_count,
                    "like_count": post.like_count,
                },
            )
            session.add(result_row)
            post_results.append(
                {
                    "post_id": str(post.id),
                    "sentiment_score": sentiment_value,
                    "fake_comment_risk": fake_value,
                    "engagement_quality": engagement_value,
                }
            )
            publish_event(
                campaign_id,
                "deep_analysis.post_analyzed",
                run_id=run_id,
                influencer_id=influencer_id,
                post_id=str(post.id),
            )

        audience_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 50.0
        fake_engagement_risk = sum(fake_risks) / len(fake_risks) if fake_risks else 0.0
        overall_grade = _grade_from_scores(audience_sentiment, fake_engagement_risk)
        report_payload = {
            "influencer_id": influencer_id,
            "campaign_id": campaign_id,
            "comment_count": len(comments),
            "post_results": post_results,
            "provider_coverage": enrichment.get("coverage", {}),
            "recommendation": _recommendation(audience_sentiment, fake_engagement_risk),
        }
        report = models.DeepAnalysisReport(
            id=uuid4(),
            run_id=run_uuid,
            overall_grade=overall_grade,
            audience_sentiment=round(audience_sentiment, 2),
            fake_engagement_risk=round(fake_engagement_risk, 2),
            brand_safety_summary="No additional brand-safety issues beyond campaign scoring.",
            recommendation=report_payload["recommendation"],
            confidence="High" if len(comments) >= 100 else "Medium" if comments else "Low",
            report_payload=report_payload,
        )
        session.add(report)
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        report_id = str(report.id)

    publish_event(
        campaign_id,
        "deep_analysis.report_ready",
        run_id=run_id,
        influencer_id=influencer_id,
        report_id=report_id,
    )
    return {
        "status": "completed",
        "run_id": run_id,
        "report_id": report_id,
        "comment_count": len(comments),
    }


def _grade_from_scores(sentiment: float, fake_risk: float) -> str:
    adjusted = sentiment - fake_risk * 0.4
    if adjusted >= 80:
        return "A"
    if adjusted >= 70:
        return "B"
    if adjusted >= 60:
        return "C"
    if adjusted >= 40:
        return "D"
    return "F"


def _recommendation(sentiment: float, fake_risk: float) -> str:
    if fake_risk >= 70:
        return "Proceed with caution; engagement authenticity looks weak."
    if sentiment >= 70:
        return "Strong audience sentiment supports partnership."
    if sentiment >= 55:
        return "Mixed audience sentiment; review evidence before contracting."
    return "Weak audience sentiment; consider other shortlisted creators."


__all__ = ["deep_analyze"]
