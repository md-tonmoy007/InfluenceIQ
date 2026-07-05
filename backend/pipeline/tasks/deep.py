"""Deep analysis Celery tasks — staged v1 workflow.

Internal stages (within one Celery task):
  1. collect_social_content   – fetch/recent posts per platform
  2. collect_post_comments    – per-post comment sample
  3. collect_external_signals – Google Trends / search visibility
  4. synthesize_report        – score, summarise, store dossier
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.core.celery.app import celery_app
from backend.core.database import models
from backend.pipeline.analysis.engagement_quality import engagement_quality_score
from backend.pipeline.analysis.external_signals import collect_external_signals
from backend.pipeline.analysis.fake_comment import score_fake_comments
from backend.pipeline.analysis.sentiment import analyze_sentiment
from backend.pipeline.candidate.builder import build_influencer_candidate
from backend.pipeline.content.enrichment import enrich_influencer_platforms
from backend.pipeline.tasks._common import db_session, publish_event

log = logging.getLogger(__name__)

_REPORT_VERSION = "v1"
_CACHE_TTL_MINUTES = 30
_POST_LIMIT = 20
_COMMENT_PER_POST_LIMIT = 200


@celery_app.task(name="backend.pipeline.tasks.deep.deep_analyze", bind=True, max_retries=1)
def deep_analyze(
    self,
    campaign_id: str,
    influencer_id: str,
    run_id: str,
    *,
    comment_target: int = 2000,
) -> dict:
    """Orchestrate the staged v1 deep-analysis workflow."""
    log.info("deep_analyze campaign_id=%s influencer_id=%s run_id=%s", campaign_id, influencer_id, run_id)
    try:
        campaign_uuid = UUID(campaign_id)
        influencer_uuid = UUID(influencer_id)
        run_uuid = UUID(run_id)
    except (TypeError, ValueError):
        return {"status": "invalid_id"}

    publish_event(campaign_id, "deep_analysis.started", run_id=run_id, influencer_id=influencer_id)

    try:
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, run_uuid)
            if run is None:
                return {"status": "missing_run"}

            run.status = "running"
            run.started_at = datetime.now(UTC)
            run.requested_comment_target = comment_target
            run.requested_post_limit = _POST_LIMIT
            run.requested_comment_limit = _COMMENT_PER_POST_LIMIT
            run.report_version = _REPORT_VERSION

            # --- Stage 1: collect_social_content ---
            social = _collect_social_content(session, campaign_uuid, influencer_uuid, run, campaign_id, influencer_id, run_id)
            publish_event(
                campaign_id,
                "deep_analysis.social_collected",
                run_id=run_id,
                influencer_id=influencer_id,
                platform_count=social.get("platform_count", 0),
                post_count=social.get("post_count", 0),
            )

            # --- Stage 2: collect_post_comments ---
            comments = _collect_post_comments(session, influencer_uuid, run, campaign_id, influencer_id, run_id)
            publish_event(
                campaign_id,
                "deep_analysis.comments_collected",
                run_id=run_id,
                influencer_id=influencer_id,
                comment_count=run.collected_comment_count,
            )

            # --- Stage 3: collect_external_signals ---
            candidate = build_influencer_candidate(session, influencer_uuid, campaign_uuid, comment_limit=comment_target)
            external = _collect_external(candidate, campaign_id, influencer_id, run_id)
            publish_event(
                campaign_id,
                "deep_analysis.external_signals_collected",
                run_id=run_id,
                influencer_id=influencer_id,
                coverage=external.get("_coverage", {}),
            )

            # --- Stage 4: synthesize_report ---
            report_id = _synthesize_report(
                session,
                run,
                social,
                comments,
                external,
                candidate,
                campaign_id,
                influencer_id,
                run_id,
                campaign_uuid,
                influencer_uuid,
            )
    except Exception as exc:
        log.exception("deep_analyze failed campaign_id=%s influencer_id=%s run_id=%s", campaign_id, influencer_id, run_id)
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, UUID(run_id))
            if run:
                run.status = "failed"
                run.failed_at = datetime.now(UTC)
                run.failure_reason = str(exc)[:4000]
        publish_event(
            campaign_id,
            "deep_analysis.failed",
            run_id=run_id,
            influencer_id=influencer_id,
            error=str(exc),
        )
        raise

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
        "comment_count": run.collected_comment_count,
    }


def _collect_social_content(
    session,
    campaign_uuid: UUID,
    influencer_uuid: UUID,
    run: models.DeepAnalysisRun,
    campaign_id: str,
    influencer_id: str,
    run_id: str,
) -> dict:
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
    run.provider_coverage = enrichment.get("coverage", {})

    posts = (
        session.query(models.PlatformPost)
        .join(models.PlatformProfile)
        .filter(models.PlatformProfile.influencer_id == influencer_uuid)
        .order_by(models.PlatformPost.published_at.desc().nullslast())
        .limit(_POST_LIMIT)
        .all()
    )

    coverage = _build_coverage_summary(enrichment.get("coverage", {}), posts)
    run.coverage_summary = coverage

    return {
        "platform_count": len(enrichment.get("coverage", {})),
        "post_count": len(posts),
        "coverage": coverage,
    }


def _build_coverage_summary(provider_coverage: dict, posts: list) -> dict:
    platforms: dict[str, dict] = {}
    for post in posts:
        platform = post.platform
        if platform not in platforms:
            platforms[platform] = {"posts": 0, "comments": False}
        platforms[platform]["posts"] += 1

    summary: dict[str, dict] = {}
    for key, status in provider_coverage.items():
        platform = _platform_from_url(key)
        summary[platform] = {
            "profile_status": status,
            "posts_fetched": platforms.get(platform, {}).get("posts", 0),
            "comments_fetched": platforms.get(platform, {}).get("comments", False),
        }
    return summary


def _platform_from_url(url: str) -> str:
    lower = url.lower()
    if "instagram" in lower:
        return "instagram"
    if "tiktok" in lower:
        return "tiktok"
    if "youtube" in lower or "youtu.be" in lower:
        return "youtube"
    if "x.com" in lower or "twitter" in lower:
        return "x"
    return "unknown"


def _collect_post_comments(
    session,
    influencer_uuid: UUID,
    run: models.DeepAnalysisRun,
    campaign_id: str,
    influencer_id: str,
    run_id: str,
) -> dict:
    posts = (
        session.query(models.PlatformPost)
        .join(models.PlatformProfile)
        .filter(models.PlatformProfile.influencer_id == influencer_uuid)
        .order_by(models.PlatformPost.published_at.desc().nullslast())
        .limit(_POST_LIMIT)
        .all()
    )

    total_comments = 0
    for post in posts:
        post_comments = (
            session.query(models.PlatformComment)
            .filter(models.PlatformComment.platform_post_id == post.id)
            .limit(_COMMENT_PER_POST_LIMIT)
            .all()
        )
        total_comments += len(post_comments)

    run.collected_comment_count = total_comments
    return {"post_count": len(posts), "total_comments": total_comments}


def _collect_external(candidate: dict, campaign_id: str, influencer_id: str, run_id: str) -> dict:
    creator_name = str(candidate.get("canonical_name", ""))
    handle_variants = _handle_variants(candidate)
    topic_variants: list[str] = []
    platforms = candidate.get("platforms", {})
    if isinstance(platforms, dict):
        for platform_name, url in platforms.items():
            if isinstance(url, str):
                topic_variants.append(platform_name)

    try:
        external = collect_external_signals(
            creator_name,
            handle_variants=handle_variants,
            topic_variants=topic_variants,
        )
    except Exception as exc:
        log.warning("collect_external_signals failed: %s", exc)
        external = {
            "google_trends": None,
            "search_visibility": None,
            "web_sentiment": None,
            "_coverage": {
                "google_trends": "error",
                "search_visibility": "error",
                "web_sentiment": "error",
            },
        }
    return external


def _handle_variants(candidate: dict) -> list[str]:
    handles: list[str] = []
    platforms = candidate.get("platforms", {})
    if isinstance(platforms, dict):
        for raw in platforms.values():
            if isinstance(raw, str):
                import re
                match = re.search(r"(?:x\.com|twitter\.com|instagram\.com|tiktok\.com)/?(\w+)", raw)
                if match:
                    handles.append(match.group(1))
    return handles


def _synthesize_report(
    session,
    run: models.DeepAnalysisRun,
    social: dict,
    comments: dict,
    external: dict,
    candidate: dict,
    campaign_id: str,
    influencer_id: str,
    run_id: str,
    campaign_uuid: UUID,
    influencer_uuid: UUID,
) -> str:
    run_uuid = UUID(run_id)
    influencer_uid = UUID(influencer_id)

    posts = (
        session.query(models.PlatformPost)
        .join(models.PlatformProfile)
        .filter(models.PlatformProfile.influencer_id == influencer_uuid)
        .order_by(models.PlatformPost.published_at.desc().nullslast())
        .limit(_POST_LIMIT)
        .all()
    )

    post_results: list[dict] = []
    sentiment_scores: list[float] = []
    fake_risks: list[float] = []
    engagement_scores: list[float] = []
    posts_analyzed: list[dict] = []

    for post in posts:
        post_comments = [
            row.text
            for row in session.query(models.PlatformComment)
            .filter(models.PlatformComment.platform_post_id == post.id)
            .limit(_COMMENT_PER_POST_LIMIT)
            .all()
            if row.text
        ]
        if not post_comments:
            posts_analyzed.append({
                "post_id": str(post.id),
                "platform": post.platform,
                "comment_count": 0,
                "status": "no_comments",
            })
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

        post_results.append({
            "post_id": str(post.id),
            "sentiment_score": sentiment_value,
            "fake_comment_risk": fake_value,
            "engagement_quality": engagement_value,
        })
        posts_analyzed.append({
            "post_id": str(post.id),
            "platform": post.platform,
            "comment_count": len(post_comments),
            "sentiment_score": sentiment_value,
            "fake_comment_risk": fake_value,
            "engagement_quality": engagement_value,
            "status": "ok",
        })

    audience_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 50.0
    fake_engagement_risk = sum(fake_risks) / len(fake_risks) if fake_risks else 0.0
    overall_grade = _grade_from_scores(audience_sentiment, fake_engagement_risk)

    total_comments = run.collected_comment_count
    confidence = _derive_confidence(total_comments, external, posts_analyzed)

    strengths, risks = _derive_strengths_risks(audience_sentiment, fake_engagement_risk, external)
    recommendation = _build_recommendation(audience_sentiment, fake_engagement_risk, total_comments)

    # Build v1 report payload
    report_payload = {
        "creator_summary": {
            "name": candidate.get("canonical_name", ""),
            "primary_platform": candidate.get("primary_platform", ""),
            "followers": candidate.get("followers", 0),
            "engagement_rate": candidate.get("engagement_rate", 0),
            "verified": candidate.get("verified", False),
        },
        "campaign_fit_summary": recommendation,
        "platform_coverage": run.coverage_summary or {},
        "posts_analyzed": posts_analyzed,
        "comments_analyzed": total_comments,
        "audience_signals": {
            "sentiment": round(audience_sentiment, 2),
            "fake_engagement_risk": round(fake_engagement_risk, 2),
            "grade": overall_grade,
        },
        "popularity_signals": external.get("google_trends") or {},
        "brand_safety_signals": {
            "search_visibility": external.get("search_visibility"),
            "web_sentiment": external.get("web_sentiment"),
        },
        "key_strengths": strengths,
        "key_risks": risks,
        "recommendation": recommendation,
        "confidence_reasoning": confidence.get("reasoning", ""),
        "citations": _build_citations(posts_analyzed, external),
    }

    report = models.DeepAnalysisReport(
        id=uuid4(),
        run_id=run_uuid,
        overall_grade=overall_grade,
        audience_sentiment=round(audience_sentiment, 2),
        fake_engagement_risk=round(fake_engagement_risk, 2),
        brand_safety_summary=_brand_safety_summary(external),
        recommendation=recommendation,
        confidence=confidence.get("level", "Low"),
        report_payload=report_payload,
    )
    session.add(report)

    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.cache_expires_at = datetime.now(UTC) + timedelta(minutes=_CACHE_TTL_MINUTES)

    return str(report.id)


def _derive_confidence(total_comments: int, external: dict, posts_analyzed: list[dict]) -> dict:
    reasoning_parts: list[str] = []
    score = 0.0

    if total_comments >= 100:
        score += 0.4
        reasoning_parts.append("sufficient comment volume")
    elif total_comments > 0:
        score += 0.2
        reasoning_parts.append("limited comment volume")
    else:
        reasoning_parts.append("no comments available")

    analyzed_posts = [p for p in posts_analyzed if p.get("status") == "ok"]
    if len(analyzed_posts) >= 10:
        score += 0.3
        reasoning_parts.append("sufficient post coverage")
    elif len(analyzed_posts) > 0:
        score += 0.15
        reasoning_parts.append("limited post coverage")
    else:
        reasoning_parts.append("no posts analyzed")

    external_cov = external.get("_coverage", {})
    trends_ok = external_cov.get("google_trends") in ("ok", "no_data")
    search_ok = external_cov.get("search_visibility") in ("ok", "no_results")
    if trends_ok or search_ok:
        score += 0.15
        reasoning_parts.append("external signals available")

    if any(p.get("status") == "no_comments" for p in posts_analyzed):
        score -= 0.1
        reasoning_parts.append("some posts lack comments")

    if score >= 0.7:
        level = "High"
    elif score >= 0.4:
        level = "Medium"
    else:
        level = "Low"

    return {"level": level, "score": round(score, 2), "reasoning": "; ".join(reasoning_parts)}


def _derive_strengths_risks(sentiment: float, fake_risk: float, external: dict) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    risks: list[str] = []

    if sentiment >= 70:
        strengths.append("Strong positive audience sentiment")
    elif sentiment >= 55:
        strengths.append("Moderately positive audience sentiment")

    if fake_risk <= 20:
        strengths.append("Low fake engagement risk")
    elif fake_risk >= 60:
        risks.append("High fake engagement risk — engagement authenticity is weak")
    elif fake_risk >= 40:
        risks.append("Elevated fake engagement risk")

    external_cov = external.get("_coverage", {})
    if external_cov.get("google_trends") == "ok":
        strengths.append("Google Trends data supports popularity assessment")
    elif external_cov.get("google_trends") == "no_data":
        risks.append("Google Trends unavailable for this creator — popularity signals limited")

    if external_cov.get("search_visibility") == "ok":
        strengths.append("External search visibility confirmed")
    elif external_cov.get("search_visibility") == "no_results":
        risks.append("Limited external search visibility")

    return strengths, risks


def _build_recommendation(sentiment: float, fake_risk: float, total_comments: int) -> str:
    if total_comments == 0:
        return "Insufficient comment data to provide a strong recommendation."
    if fake_risk >= 70:
        return "Proceed with caution; engagement authenticity looks weak."
    if sentiment >= 70:
        return "Strong audience sentiment supports partnership."
    if sentiment >= 55:
        return "Mixed audience sentiment; review evidence before contracting."
    return "Weak audience sentiment; consider other shortlisted creators."


def _build_citations(posts_analyzed: list[dict], external: dict) -> list[dict]:
    citations: list[dict] = []

    for post in posts_analyzed:
        if post.get("status") == "ok":
            citations.append({
                "source": "post",
                "post_id": post.get("post_id"),
                "platform": post.get("platform"),
                "key_metrics": {
                    "comment_count": post.get("comment_count"),
                    "sentiment_score": post.get("sentiment_score"),
                    "fake_comment_risk": post.get("fake_comment_risk"),
                },
            })

    if external.get("search_visibility"):
        urls: list[str] = []
        for result_list in external["search_visibility"].get("queries", {}).values():
            if isinstance(result_list, list):
                for item in result_list:
                    if isinstance(item, dict) and item.get("url"):
                        urls.append(item["url"])
        if urls:
            citations.append({
                "source": "search_visibility",
                "urls": urls,
            })

    return citations


def _brand_safety_summary(external: dict) -> str:
    web_sentiment = external.get("web_sentiment")
    if web_sentiment and web_sentiment.get("snippets"):
        return f"Found {len(web_sentiment['snippets'])} external mentions; review for brand-risk signals."
    return "No additional brand-safety issues beyond campaign scoring."


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


__all__ = ["deep_analyze"]
