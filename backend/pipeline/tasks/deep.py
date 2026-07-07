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
from typing import Any
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

_INSUFFICIENT_RECOMMENDATION = (
    "Insufficient data to grade this creator — re-run after enrichment completes."
)
_INSUFFICIENT_BRAND_SAFETY = (
    "Insufficient data to assess brand safety — re-run after enrichment completes."
)

_BRAND_RISK_KEYWORDS = (
    "scandal", "lawsuit", "fraud", "scam", "controversy", "controversial",
    "sued", "indicted", "plea", "settlement", "investigation", "allegation",
    "allegations", "misconduct", "harassment", "ban", "banned", "boycott",
    "fake", "deepfake", "plagiarism", "stolen", "leak", "leaked",
)


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

    final_comment_count = 0
    try:
        # We use multiple short-lived sessions so that the run row's
        # ``status``, ``collected_comment_count`` and ``coverage_summary`` are
        # visible to the polling endpoint between stages. Without this, the
        # frontend would see a single "queued → completed" transition and the
        # ``comments analyzed`` counter would stay at 0 for the entire run.
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
            run.current_stage = "starting"

        # --- Stage 1: collect_social_content ---
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, run_uuid)
            if run is None:
                return {"status": "missing_run"}
            social = _collect_social_content(
                session, campaign_uuid, influencer_uuid, run, campaign_id, influencer_id, run_id
            )
            run.current_stage = "social"
        publish_event(
            campaign_id,
            "deep_analysis.social_collected",
            run_id=run_id,
            influencer_id=influencer_id,
            platform_count=social.get("platform_count", 0),
            post_count=social.get("post_count", 0),
        )

        # --- Stage 2: collect_post_comments ---
        comments_total = 0
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, run_uuid)
            if run is None:
                return {"status": "missing_run"}
            comments = _collect_post_comments(
                session, influencer_uuid, run, campaign_id, influencer_id, run_id
            )
            social = _merge_coverage_with_comments(social, comments.get("platform_comments", {}))
            run.coverage_summary = social["coverage"]
            run.current_stage = "comments"
            # Capture before the session closes — accessing the attribute
            # after the with-block raises DetachedInstanceError.
            comments_total = int(run.collected_comment_count or 0)
        publish_event(
            campaign_id,
            "deep_analysis.comments_collected",
            run_id=run_id,
            influencer_id=influencer_id,
            comment_count=comments_total,
        )

        # --- Stage 3: collect_external_signals ---
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, run_uuid)
            if run is None:
                return {"status": "missing_run"}
            run.current_stage = "trends"
            candidate = build_influencer_candidate(
                session, influencer_uuid, campaign_uuid, comment_limit=comment_target
            )
        external = _collect_external(candidate, campaign_id, influencer_id, run_id)
        publish_event(
            campaign_id,
            "deep_analysis.external_signals_collected",
            run_id=run_id,
            influencer_id=influencer_id,
            coverage=external.get("_coverage", {}),
        )

        # --- Stage 4: synthesize_report ---
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, run_uuid)
            if run is None:
                return {"status": "missing_run"}
            run.current_stage = "synthesizing"
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
            # Capture before the session closes.
            final_comment_count = int(run.collected_comment_count or 0)
    except Exception as exc:
        log.exception("deep_analyze failed campaign_id=%s influencer_id=%s run_id=%s", campaign_id, influencer_id, run_id)
        with db_session() as session:
            run = session.get(models.DeepAnalysisRun, UUID(run_id))
            if run:
                run.status = "failed"
                run.failed_at = datetime.now(UTC)
                run.current_stage = "failed"
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
        "comment_count": final_comment_count,
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
    """Build the per-platform coverage summary used by the report page.

    ``comments_fetched`` is initialised to ``False`` and only flipped to
    ``True`` by :func:`_merge_coverage_with_comments` once the comment
    stage has actually run for that platform. This is the source of truth
    for the "ok / unavailable" badge in the Platform coverage card; we
    never want to render "ok" for a platform whose comment stage was
    skipped.
    """
    platforms: dict[str, dict] = {}
    for post in posts:
        platform = post.platform
        if platform not in platforms:
            platforms[platform] = {"posts": 0, "comments": False}
        platforms[platform]["posts"] += 1

    summary: dict[str, dict] = {}
    for key, status in provider_coverage.items():
        platform = _platform_from_url(key)
        post_count = platforms.get(platform, {}).get("posts", 0)
        effective_status = status
        if status == "ok" and post_count == 0:
            effective_status = "no_posts"
        summary[platform] = {
            "profile_status": effective_status,
            "posts_fetched": post_count,
            "comments_fetched": False,
            "comments_analyzed": 0,
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
    per_platform: dict[str, int] = {}
    for post in posts:
        post_comments = (
            session.query(models.PlatformComment)
            .filter(models.PlatformComment.platform_post_id == post.id)
            .limit(_COMMENT_PER_POST_LIMIT)
            .all()
        )
        total_comments += len(post_comments)
        per_platform[post.platform] = per_platform.get(post.platform, 0) + len(post_comments)

    run.collected_comment_count = total_comments
    return {
        "post_count": len(posts),
        "total_comments": total_comments,
        "platform_comments": per_platform,
    }


def _merge_coverage_with_comments(social: dict, platform_comments: dict[str, int]) -> dict:
    """Stamp the comment-fetch result into the per-platform coverage summary.

    ``_build_coverage_summary`` only had access to post counts and the
    provider URL status; it could not tell whether the comment-fetch stage
    actually ran for each platform. ``_collect_post_comments`` now returns
    per-platform comment counts; this helper mutates the coverage dict in
    place so the frontend can render the right badge.
    """
    coverage = social.get("coverage") or {}
    for platform, info in coverage.items():
        info["comments_fetched"] = platform in platform_comments
        info["comments_analyzed"] = int(platform_comments.get(platform, 0))
    social["coverage"] = coverage
    return social


_ENGAGEMENT_QUALITY_FEATURE_KEYS = (
    "diverse_comments_score",
    "context_relevant_comments_score",
    "stable_engagement_rate_score",
    "realistic_like_comment_ratio_score",
    "organic_source_diversity_score",
)


def _engagement_quality_features(candidate: dict) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    return {key: candidate.get(key, 0.0) for key in _ENGAGEMENT_QUALITY_FEATURE_KEYS}


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

    def _raw_value(post, *keys: str):
        raw = post.raw if isinstance(post.raw, dict) else {}
        for key in keys:
            value = raw.get(key)
            if value not in (None, ""):
                return value
        return None

    def _first_text(*values) -> str | None:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value
        return None

    def _first_int(*values) -> int | None:
        for value in values:
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    for post in posts:
        post_comments = [
            row.text
            for row in session.query(models.PlatformComment)
            .filter(models.PlatformComment.platform_post_id == post.id)
            .limit(_COMMENT_PER_POST_LIMIT)
            .all()
            if row.text
        ]
        title = _first_text(post.title, _raw_value(post, "title"))
        caption = _first_text(
            post.caption,
            _raw_value(post, "caption", "description", "text"),
        )
        post_url = _first_text(
            post.post_url,
            _raw_value(post, "url", "post_url", "link"),
        )
        like_count = _first_int(post.like_count, _raw_value(post, "like_count", "likes"))
        view_count = _first_int(post.view_count, _raw_value(post, "view_count", "views"))

        if not post_comments:
            posts_analyzed.append({
                "post_id": str(post.id),
                "platform": post.platform,
                "title": title,
                "caption": caption,
                "post_url": post_url,
                "like_count": like_count,
                "view_count": view_count,
                "comment_count": 0,
                "status": "no_comments",
            })
            continue

        sentiment = analyze_sentiment(post_comments)
        fake = score_fake_comments(comments=post_comments)
        engagement = engagement_quality_score(
            float(fake.get("fake_comment_risk_score", 0.0)),
            features=_engagement_quality_features(candidate),
        )

        sentiment_value = float(sentiment.get("sentiment_score", 50.0))
        fake_value = float(fake.get("fake_comment_risk_score", 0.0))
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
            "title": title,
            "caption": caption,
            "post_url": post_url,
            "like_count": like_count,
            "view_count": view_count,
            "comment_count": len(post_comments),
            "sentiment_score": sentiment_value,
            "fake_comment_risk": fake_value,
            "engagement_quality": engagement_value,
            "status": "ok",
        })

    audience_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 50.0
    fake_engagement_risk = sum(fake_risks) / len(fake_risks) if fake_risks else 0.0
    analyzed_posts = [p for p in posts_analyzed if p.get("status") == "ok"]
    has_data = bool(analyzed_posts) and int(run.collected_comment_count or 0) > 0
    overall_grade = _grade_from_scores(
        audience_sentiment, fake_engagement_risk, has_data=has_data
    )

    total_comments = run.collected_comment_count
    confidence = _derive_confidence(total_comments, external, posts_analyzed)

    strengths, risks = _derive_strengths_risks(
        audience_sentiment, fake_engagement_risk, external, has_data=has_data
    )
    recommendation = _build_recommendation(
        audience_sentiment, fake_engagement_risk, total_comments, has_data=has_data
    )

    # Build v1 report payload
    report_payload = {
        "creator_summary": {
            "name": candidate.get("canonical_name", ""),
            "primary_platform": candidate.get("primary_platform", ""),
            "followers": candidate.get("followers", 0),
            "engagement_rate": candidate.get("engagement_rate", 0),
            "verified": candidate.get("verified", False),
        },
        "data_sufficiency": {
            "has_data": has_data,
            "analyzed_posts": len(analyzed_posts),
            "total_comments": int(total_comments or 0),
            "grade": overall_grade,
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
            "mention_count": _brand_mention_count(external, has_data=has_data),
            "flagged_count": _brand_flagged_count(external, has_data=has_data),
        },
        "key_strengths": strengths,
        "key_risks": risks,
        "recommendation": recommendation,
        "confidence_reasoning": confidence.get("reasoning", ""),
        "citations": _build_citations(posts_analyzed, external, has_data=has_data),
    }

    report = models.DeepAnalysisReport(
        id=uuid4(),
        run_id=run_uuid,
        overall_grade=overall_grade,
        audience_sentiment=round(audience_sentiment, 2),
        fake_engagement_risk=round(fake_engagement_risk, 2),
        brand_safety_summary=_brand_safety_summary(external, has_data=has_data),
        recommendation=recommendation,
        confidence=confidence.get("level", "Low"),
        report_payload=report_payload,
    )
    session.add(report)

    run.status = "completed"
    run.current_stage = "done"
    run.completed_at = datetime.now(UTC)
    run.cache_expires_at = datetime.now(UTC) + timedelta(minutes=_CACHE_TTL_MINUTES)

    return str(report.id)


def _derive_confidence(total_comments: int, external: dict, posts_analyzed: list[dict]) -> dict:
    reasoning_parts: list[str] = []
    score = 0.0

    analyzed_posts = [p for p in posts_analyzed if p.get("status") == "ok"]
    has_data = bool(analyzed_posts) and int(total_comments or 0) > 0

    if not has_data:
        reasoning_parts.append("insufficient evidence — no analyzed posts and no comments")
        return {"level": "Low", "score": 0.0, "reasoning": "; ".join(reasoning_parts)}

    if total_comments >= 100:
        score += 0.4
        reasoning_parts.append("sufficient comment volume")
    elif total_comments > 0:
        score += 0.2
        reasoning_parts.append("limited comment volume")
    else:
        reasoning_parts.append("no comments available")

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


def _derive_strengths_risks(
    sentiment: float,
    fake_risk: float,
    external: dict,
    *,
    has_data: bool,
) -> tuple[list[str], list[str]]:
    """Compute strengths and risks, gated on whether we actually have evidence.

    The previous implementation unconditionally asserted "Low fake engagement
    risk" whenever the fake-risk default was 0 — which happens whenever we
    have no analyzed posts. That's a contradiction: the recommendation text
    at the same time said "Insufficient comment data". With ``has_data``
    False we instead surface a single "Insufficient evidence" note so the
    user can tell the strengths list is a placeholder, not a verdict.
    """
    strengths: list[str] = []
    risks: list[str] = []

    if not has_data:
        return (
            ["Insufficient evidence to assess creator strengths — no analyzed posts or comments."],
            ["Re-run after enrichment completes to generate strengths and risks."],
        )

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


def _build_recommendation(sentiment: float, fake_risk: float, total_comments: int, *, has_data: bool) -> str:
    if not has_data:
        return _INSUFFICIENT_RECOMMENDATION
    if total_comments == 0:
        return "Insufficient comment data to provide a strong recommendation."
    if fake_risk >= 70:
        return "Proceed with caution; engagement authenticity looks weak."
    if sentiment >= 70:
        return "Strong audience sentiment supports partnership."
    if sentiment >= 55:
        return "Mixed audience sentiment; review evidence before contracting."
    return "Weak audience sentiment; consider other shortlisted creators."


def _build_citations(posts_analyzed: list[dict], external: dict, *, has_data: bool) -> list[dict]:
    citations: list[dict] = []

    for post in posts_analyzed:
        if post.get("status") == "ok":
            citations.append({
                "source": "post",
                "post_id": post.get("post_id"),
                "platform": post.get("platform"),
                "title": post.get("title"),
                "url": post.get("post_url"),
                "key_metrics": {
                    "comment_count": post.get("comment_count"),
                    "sentiment_score": post.get("sentiment_score"),
                    "fake_comment_risk": post.get("fake_comment_risk"),
                },
            })

    if external.get("search_visibility") and has_data:
        urls: list[str] = []
        for result_list in external["search_visibility"].get("queries", {}).values():
            if isinstance(result_list, list):
                for item in result_list:
                    if isinstance(item, dict) and item.get("url"):
                        url_value = str(item["url"])
                        if any(domain in url_value.lower() for domain in _PROFILE_DOMAINS):
                            continue
                        if "search_query=" in url_value.lower():
                            continue
                        urls.append(url_value)
        if urls:
            citations.append({
                "source": "search_visibility",
                "urls": urls,
            })

    return citations


def _flag_brand_risk(snippet: dict) -> bool:
    """Best-effort risk flag using keyword scan over title + snippet text.

    Cheap, deterministic, and a strict subset of the more thorough
    ``brand_safety_blocklist`` scan used by the main role-4 pipeline. The
    goal is to give the user a real signal — not just a count of search
    API results — so the report says e.g. "9 mentions (2 flagged)" rather
    than "9 mentions".
    """
    text = " ".join(
        str(snippet.get(field, "")) for field in ("title", "snippet", "url")
    ).lower()
    return any(keyword in text for keyword in _BRAND_RISK_KEYWORDS)


def _brand_safety_summary(external: dict, *, has_data: bool) -> str:
    if not has_data:
        return _INSUFFICIENT_BRAND_SAFETY
    substantive = _substantive_mentions(external)
    if not substantive:
        return "No additional brand-safety issues beyond campaign scoring."
    total = len(substantive)
    flagged = sum(1 for snippet in substantive if _flag_brand_risk(snippet))
    if flagged == 0:
        return f"Found {total} external mentions; none flagged for review."
    return f"Found {total} external mentions ({flagged} flagged for review); review for brand-risk signals."


_PROFILE_DOMAINS = (
    "collabstr.com",
    "linkedin.com",
    "facebook.com/groups",
    "instagram.com",
    "vercel.app",
    "github.com",
)


def _substantive_mentions(external: dict) -> list[dict]:
    web_sentiment = external.get("web_sentiment") or {}
    snippets = web_sentiment.get("snippets") or []
    return [snippet for snippet in snippets if _is_substantive_mention(snippet)]


def _brand_mention_count(external: dict, *, has_data: bool) -> int:
    if not has_data:
        return 0
    return len(_substantive_mentions(external))


def _brand_flagged_count(external: dict, *, has_data: bool) -> int:
    if not has_data:
        return 0
    return sum(1 for snippet in _substantive_mentions(external) if _flag_brand_risk(snippet))


def _is_substantive_mention(snippet: dict) -> bool:
    """Drop profile/marketplace pages and search-result pages.

    SERP API returns a mix of real articles, social profile pages, and
    search-result pages that echo the query (e.g. YouTube search for
    "<name> controversy"). Counting those as "mentions" and keyword-
    scanning their titles inflates the brand-safety count and produces
    false positives.
    """
    url = str(snippet.get("url") or "").lower()
    title = str(snippet.get("title") or "").strip()
    snippet_text = str(snippet.get("snippet") or "").strip()
    if not url or not title or not snippet_text:
        return False
    if any(domain in url for domain in _PROFILE_DOMAINS):
        return False
    if "/results?search_query=" in url or "search_query=" in url:
        return False
    if "search results for" in title.lower() or "results related to" in title.lower():
        return False
    return True


_NO_GRADE = "N/A"


def _grade_from_scores(sentiment: float, fake_risk: float, *, has_data: bool) -> str:
    if not has_data:
        return _NO_GRADE
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
