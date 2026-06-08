from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session
import structlog

from app.celery_app import celery_app
from app.db import SessionLocal
from app.logging_config import bind_campaign, clear_log_context
from app.models import Campaign, InfluencerResult
from app.services.pipeline_state import emit_event, update_state

logger = structlog.get_logger(__name__)


@dataclass
class PipelineInfluencer:
    influencer_id: str
    name: str
    handle: str
    platform: str
    citations: list[str]
    brand_safety_flags: list[str]
    source_payload: dict[str, Any]
    score_payload: dict[str, Any]


def start_campaign_pipeline(campaign_id: str) -> None:
    thread = threading.Thread(target=run_campaign_pipeline, args=(campaign_id,), daemon=True)
    thread.start()


def run_campaign_pipeline(campaign_id: str) -> None:
    bind_campaign(campaign_id)
    started_at = time.monotonic()
    session = SessionLocal()
    try:
        campaign = session.get(Campaign, uuid.UUID(campaign_id))
        if campaign is None:
            logger.warning("campaign_missing_for_pipeline")
            return

        bind_campaign(campaign_id, brand=campaign.brand, product=campaign.product)
        logger.info("campaign_pipeline_started")
        campaign.status = "running"
        session.commit()

        update_state(
            campaign_id,
            status="running",
            phase="queued",
            urls_discovered=0,
            urls_scraped=0,
            influencers_found=0,
            scores_computed=0,
        )
        emit_event(campaign_id, "pipeline.started", {"campaign_id": campaign_id})

        logger.info("campaign_pipeline_phase_started", phase="search")
        queries = _dispatch("app.tasks.search.generate_queries", campaign_id)
        all_results: list[dict[str, Any]] = []
        for query in queries:
            all_results.extend(_dispatch("app.tasks.search.execute_search", campaign_id, query))

        unique_urls = list(OrderedDict((result["url"], result) for result in all_results).values())
        update_state(campaign_id, phase="search", urls_discovered=len(unique_urls))
        logger.info("campaign_pipeline_phase_completed", phase="search", urls_discovered=len(unique_urls))

        by_name: dict[str, PipelineInfluencer] = {}
        urls_scraped = 0
        scores_computed = 0

        for result in unique_urls:
            logger.info("campaign_pipeline_url_started", url=result["url"])
            page = _dispatch("app.tasks.crawl.fetch_page", campaign_id, result["url"])
            content = _dispatch("app.tasks.crawl.extract_content", page)
            brand_safety = _dispatch("app.tasks.score.classify_brand_safety", campaign_id, content)
            mentions = _dispatch("app.tasks.extract.extract_influencers", campaign_id, content)

            urls_scraped += 1
            update_state(campaign_id, phase="crawl", urls_scraped=urls_scraped)

            for mention in mentions:
                canonical_key = _canonical_key(mention)
                platform, handle = _platform_and_handle(mention)
                sub_scores = _build_sub_scores(content, mention, brand_safety)
                influencer_id = by_name.get(canonical_key, None).influencer_id if canonical_key in by_name else str(uuid.uuid4())
                score = _dispatch("app.tasks.score.score_influencer", campaign_id, influencer_id, sub_scores)
                scores_computed += 1

                influencer = PipelineInfluencer(
                    influencer_id=influencer_id,
                    name=mention.get("name") or handle or "Unknown Creator",
                    handle=handle,
                    platform=platform,
                    citations=sorted({mention.get("source_url", ""), content.get("url", "")} - {""}),
                    brand_safety_flags=[reason for reason in brand_safety.get("reasons", []) if not reason.startswith("No deterministic")],
                    source_payload={
                        "search_result": result,
                        "content": content,
                        "mention": mention,
                        "brand_safety": brand_safety,
                    },
                    score_payload=score,
                )
                by_name[canonical_key] = influencer
                update_state(
                    campaign_id,
                    phase="score",
                    influencers_found=len(by_name),
                    scores_computed=scores_computed,
                )
            logger.info(
                "campaign_pipeline_url_completed",
                url=result["url"],
                mentions=len(mentions),
                urls_scraped=urls_scraped,
                scores_computed=scores_computed,
            )

        _replace_influencers(session, campaign, by_name.values())
        campaign.status = "completed"
        session.commit()

        duration_seconds = round(time.monotonic() - started_at, 2)
        update_state(campaign_id, status="completed", phase="completed", duration_seconds=duration_seconds)
        emit_event(
            campaign_id,
            "pipeline.completed",
            {"total_influencers": len(by_name), "duration_seconds": duration_seconds},
        )
        logger.info(
            "campaign_pipeline_completed",
            total_influencers=len(by_name),
            duration_seconds=duration_seconds,
        )
    except Exception as exc:
        logger.exception("campaign_pipeline_failed")
        campaign = session.get(Campaign, uuid.UUID(campaign_id))
        if campaign is not None:
            campaign.status = "failed"
            session.commit()
        update_state(campaign_id, status="failed", phase="failed", error=str(exc))
        emit_event(campaign_id, "pipeline.failed", {"error": str(exc)})
    finally:
        session.close()
        clear_log_context()


def _dispatch(task_name: str, *args: Any) -> Any:
    started_at = time.monotonic()
    logger.info("celery_task_dispatch_started", task_name=task_name)
    try:
        result = celery_app.send_task(task_name, args=args).get(timeout=60)
    except Exception:
        logger.exception("celery_task_dispatch_failed", task_name=task_name)
        raise
    logger.info(
        "celery_task_dispatch_completed",
        task_name=task_name,
        duration_seconds=round(time.monotonic() - started_at, 3),
    )
    return result


def _canonical_key(mention: dict[str, Any]) -> str:
    name = str(mention.get("name") or "").strip().lower()
    if name:
        return name
    _, handle = _platform_and_handle(mention)
    return handle.lower()


def _platform_and_handle(mention: dict[str, Any]) -> tuple[str, str]:
    platforms = mention.get("platforms") or {}
    if isinstance(platforms, dict) and platforms:
        platform, handle = next(iter(platforms.items()))
        return platform, str(handle)
    return "unknown", ""


def _build_sub_scores(content: dict[str, Any], mention: dict[str, Any], brand_safety: dict[str, Any]) -> dict[str, int]:
    credentials = mention.get("credentials") or []
    content_text = str(content.get("content") or "")
    risk_count = sum(1 for value in (brand_safety.get("risks") or {}).values() if value)

    relevance = 88 if any(term in content_text.lower() for term in ("creator", "educator", "influencer")) else 72
    credibility = 90 if credentials else 68
    engagement = 78 if mention.get("platforms") else 60
    sentiment = 82 if "positive" in content_text.lower() or "evidence-based" in content_text.lower() else 70
    brand_safety_score = max(0, 100 - (risk_count * 25))

    return {
        "relevance": relevance,
        "credibility": credibility,
        "engagement": engagement,
        "sentiment": sentiment,
        "brand_safety": brand_safety_score,
        "data_source_count": max(1, len({mention.get("source_url"), content.get("url")} - {None, ""})),
    }


def _replace_influencers(session: Session, campaign: Campaign, influencers: Any) -> None:
    session.query(InfluencerResult).filter(InfluencerResult.campaign_id == campaign.campaign_id).delete()
    for influencer in influencers:
        score_payload = influencer.score_payload
        session.add(
            InfluencerResult(
                influencer_id=influencer.influencer_id,
                campaign_id=campaign.campaign_id,
                name=influencer.name,
                handle=influencer.handle,
                platform=influencer.platform,
                followers=0,
                engagement_rate=float(score_payload.get("sub_scores", {}).get("engagement", 0.0)),
                match_score=float(score_payload.get("final_score", 0.0)),
                trust_grade=str(score_payload.get("grade", "D")),
                rate="TBD",
                brand_safety_flags=influencer.brand_safety_flags,
                citations=influencer.citations,
                sub_scores=score_payload.get("sub_scores", {}),
                score_payload=score_payload,
                source_payload=influencer.source_payload,
            )
        )
    session.commit()
