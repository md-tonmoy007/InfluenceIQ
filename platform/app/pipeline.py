from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session
import structlog

from app.celery_app import celery_app
from app.config import settings
from app.db import SessionLocal
from app.logging_config import bind_campaign, clear_log_context
from app.models import Campaign, InfluencerResult
from app.services.platform_enrichment import (
    choose_preferred_identity,
    enrich_platform_profile,
    normalize_platform_identity,
)
from app.services.pipeline_state import emit_event, update_state

logger = structlog.get_logger(__name__)


@dataclass
class PipelineInfluencer:
    influencer_id: str
    canonical_key: str
    name: str
    handle: str
    platform: str
    followers: int
    engagement_rate: float
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

        by_identity: dict[str, PipelineInfluencer] = {}
        urls_scraped = 0
        scores_computed = 0
        seen_urls: set[str] = set()
        crawl_queue = deque()
        for result in unique_urls:
            _enqueue_url(
                crawl_queue,
                seen_urls,
                result["url"],
                depth=1,
                source_type="search_result",
                parent_url="",
                search_result=result,
            )

        while crawl_queue and urls_scraped < settings.CRAWL_MAX_URLS_PER_CAMPAIGN:
            item = crawl_queue.popleft()
            logger.info("campaign_pipeline_url_started", url=item["url"], depth=item["depth"])
            page = _dispatch(
                "app.tasks.crawl.fetch_page",
                campaign_id,
                item["url"],
                depth=item["depth"],
                source_type=item["source_type"],
                parent_url=item["parent_url"],
            )
            content = _dispatch("app.tasks.crawl.extract_content", page)
            brand_safety = _dispatch("app.tasks.score.classify_brand_safety", campaign_id, content)
            mentions = _dispatch("app.tasks.extract.extract_influencers", campaign_id, content)

            urls_scraped += 1
            update_state(campaign_id, phase="crawl", urls_scraped=urls_scraped)

            for link in content.get("discovered_links") or []:
                _enqueue_url(
                    crawl_queue,
                    seen_urls,
                    str(link),
                    depth=int(page.get("depth") or 1) + 1,
                    source_type=_source_type_for_link(content["url"], str(link)),
                    parent_url=content["url"],
                    search_result=None,
                )

            page_identity = normalize_platform_identity(page["url"])
            if page_identity:
                enriched = enrich_platform_profile(page_identity, page)
                record = _get_or_create_influencer(by_identity, page_identity)
                _apply_profile_enrichment(record, enriched, content, page, item.get("search_result"), brand_safety)

            for mention in mentions:
                record = _record_for_mention(by_identity, mention)
                _merge_mention(record, mention, content, page, item.get("search_result"), brand_safety)

            update_state(campaign_id, phase="extract", influencers_found=len(by_identity))
            logger.info(
                "campaign_pipeline_url_completed",
                url=item["url"],
                mentions=len(mentions),
                urls_scraped=urls_scraped,
                queued_urls=len(crawl_queue),
            )

        for influencer in by_identity.values():
            sub_scores = _build_sub_scores(influencer)
            score = _dispatch("app.tasks.score.score_influencer", campaign_id, influencer.influencer_id, sub_scores)
            influencer.score_payload = score
            scores_computed += 1
            update_state(
                campaign_id,
                phase="score",
                influencers_found=len(by_identity),
                scores_computed=scores_computed,
            )

        _replace_influencers(session, campaign, by_identity.values())
        campaign.status = "completed"
        session.commit()

        duration_seconds = round(time.monotonic() - started_at, 2)
        update_state(campaign_id, status="completed", phase="completed", duration_seconds=duration_seconds)
        emit_event(
            campaign_id,
            "pipeline.completed",
            {"total_influencers": len(by_identity), "duration_seconds": duration_seconds},
        )
        logger.info(
            "campaign_pipeline_completed",
            total_influencers=len(by_identity),
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


def _dispatch(task_name: str, *args: Any, **kwargs: Any) -> Any:
    started_at = time.monotonic()
    logger.info("celery_task_dispatch_started", task_name=task_name)
    try:
        result = celery_app.send_task(task_name, args=args, kwargs=kwargs).get(timeout=60)
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


def _identity_key(identity: dict[str, Any]) -> str:
    return str(identity.get("canonical_profile_url") or "").casefold()


def _fallback_key(name: str, handle: str) -> str:
    value = str(name or handle or "unknown creator").strip().casefold()
    return f"name:{value}"


def _get_or_create_influencer(by_identity: dict[str, PipelineInfluencer], identity: dict[str, Any]) -> PipelineInfluencer:
    key = _identity_key(identity)
    if key in by_identity:
        return by_identity[key]
    influencer = PipelineInfluencer(
        influencer_id=str(uuid.uuid4()),
        canonical_key=key,
        name=identity.get("handle_or_username") or "Unknown Creator",
        handle=str(identity.get("handle_or_username") or ""),
        platform=str(identity.get("platform") or "unknown"),
        followers=0,
        engagement_rate=0.0,
        citations=[],
        brand_safety_flags=[],
        source_payload={
            "identity": identity,
            "profiles": [],
            "mentions": [],
            "search_results": [],
            "crawl_provenance": [],
            "engagement": {"sample_size": 0},
            "supporting_sources": [],
        },
        score_payload={},
    )
    by_identity[key] = influencer
    return influencer


def _record_for_mention(by_identity: dict[str, PipelineInfluencer], mention: dict[str, Any]) -> PipelineInfluencer:
    platform_urls = [str(value) for value in (mention.get("platforms") or {}).values()]
    identity = choose_preferred_identity(platform_urls)
    if identity:
        return _get_or_create_influencer(by_identity, identity)

    key = _fallback_key(str(mention.get("name") or ""), str(mention.get("handle") or ""))
    if key not in by_identity:
        by_identity[key] = PipelineInfluencer(
            influencer_id=str(uuid.uuid4()),
            canonical_key=key,
            name=str(mention.get("name") or mention.get("handle") or "Unknown Creator"),
            handle=str(mention.get("handle") or ""),
            platform=str(mention.get("platform") or "unknown"),
            followers=0,
            engagement_rate=0.0,
            citations=[],
            brand_safety_flags=[],
            source_payload={
                "identity": {},
                "profiles": [],
                "mentions": [],
                "search_results": [],
                "crawl_provenance": [],
                "engagement": {"sample_size": 0},
                "supporting_sources": [],
            },
            score_payload={},
        )
    return by_identity[key]


def _apply_profile_enrichment(
    influencer: PipelineInfluencer,
    enriched: dict[str, Any],
    content: dict[str, Any],
    page: dict[str, Any],
    search_result: dict[str, Any] | None,
    brand_safety: dict[str, Any],
) -> None:
    influencer.platform = str(enriched.get("platform") or influencer.platform)
    influencer.handle = str(enriched.get("handle") or influencer.handle)
    influencer.followers = max(influencer.followers, int(enriched.get("followers") or 0))
    influencer.engagement_rate = max(influencer.engagement_rate, float(enriched.get("engagement_rate") or 0.0))
    if enriched.get("name"):
        influencer.name = str(enriched["name"])
    influencer.citations = sorted((set(influencer.citations) | {content.get("url", "")}) - {""})
    influencer.brand_safety_flags = sorted(
        set(influencer.brand_safety_flags)
        | {reason for reason in brand_safety.get("reasons", []) if not reason.startswith("No deterministic")}
    )
    payload = influencer.source_payload
    payload["identity"] = enriched.get("identity") or payload.get("identity") or {}
    payload["profiles"].append(enriched.get("source_payload") or {})
    if search_result:
        payload["search_results"].append(search_result)
    payload["crawl_provenance"].append(
        {
            "url": page.get("url"),
            "provider": page.get("provider"),
            "attempt_count": page.get("attempt_count"),
            "archive_fallback_used": page.get("archive_fallback_used"),
            "domain": page.get("domain"),
            "rate_limited": page.get("rate_limited"),
            "depth": page.get("depth"),
            "source_type": page.get("source_type"),
            "parent_url": page.get("parent_url"),
        }
    )
    engagement = (enriched.get("source_payload") or {}).get("engagement") or {}
    if int(engagement.get("sample_size") or 0) >= int((payload.get("engagement") or {}).get("sample_size") or 0):
        payload["engagement"] = engagement


def _merge_mention(
    influencer: PipelineInfluencer,
    mention: dict[str, Any],
    content: dict[str, Any],
    page: dict[str, Any],
    search_result: dict[str, Any] | None,
    brand_safety: dict[str, Any],
) -> None:
    if not influencer.name or influencer.name == influencer.handle:
        influencer.name = str(mention.get("name") or influencer.name)
    if not influencer.handle:
        influencer.handle = str(mention.get("handle") or influencer.handle)
    if influencer.platform == "unknown" and mention.get("platform"):
        influencer.platform = str(mention.get("platform"))
    influencer.citations = sorted(
        (set(influencer.citations) | {str(mention.get("source_url") or ""), str(content.get("url") or "")}) - {""}
    )
    influencer.brand_safety_flags = sorted(
        set(influencer.brand_safety_flags)
        | {reason for reason in brand_safety.get("reasons", []) if not reason.startswith("No deterministic")}
    )
    payload = influencer.source_payload
    payload["mentions"].append(mention)
    payload["supporting_sources"].append(
        {
            "url": content.get("url"),
            "title": content.get("title"),
            "metadata": content.get("metadata"),
        }
    )
    payload["crawl_provenance"].append(
        {
            "url": page.get("url"),
            "provider": page.get("provider"),
            "attempt_count": page.get("attempt_count"),
            "archive_fallback_used": page.get("archive_fallback_used"),
            "domain": page.get("domain"),
            "rate_limited": page.get("rate_limited"),
            "depth": page.get("depth"),
            "source_type": page.get("source_type"),
            "parent_url": page.get("parent_url"),
        }
    )
    if search_result:
        payload["search_results"].append(search_result)


def _enqueue_url(
    crawl_queue: Any,
    seen_urls: set[str],
    url: str,
    *,
    depth: int,
    source_type: str,
    parent_url: str,
    search_result: dict[str, Any] | None,
) -> None:
    if not url or url in seen_urls or depth > settings.CRAWL_MAX_DEPTH:
        return
    if len(seen_urls) >= settings.CRAWL_MAX_URLS_PER_CAMPAIGN:
        return
    seen_urls.add(url)
    crawl_queue.append(
        {
            "url": url,
            "depth": depth,
            "source_type": source_type,
            "parent_url": parent_url,
            "search_result": search_result,
        }
    )


def _source_type_for_link(parent_url: str, link: str) -> str:
    identity = normalize_platform_identity(link)
    if identity:
        return f"{identity['platform']}_profile"
    return "same_domain_profile"


def _build_sub_scores(influencer: PipelineInfluencer) -> dict[str, int]:
    mentions = influencer.source_payload.get("mentions") or []
    contexts = " ".join(str(mention.get("context") or "") for mention in mentions)
    credentials = [credential for mention in mentions for credential in (mention.get("credentials") or [])]
    verified = any(bool(profile.get("verified")) for profile in influencer.source_payload.get("profiles") or [])
    sample = influencer.source_payload.get("engagement") or {}
    sample_size = int(sample.get("sample_size") or 0)
    risk_count = len(influencer.brand_safety_flags)

    relevance = 88 if any(term in contexts.lower() for term in ("creator", "educator", "influencer", "coach")) else 72
    credibility = 92 if verified else (88 if credentials else 68)
    engagement = 58
    if influencer.followers > 0 or influencer.engagement_rate > 0:
        engagement = 72
    if sample_size >= 5:
        engagement += 8
    if sample_size >= 10:
        engagement += 7
    if influencer.engagement_rate >= 0.03:
        engagement += 4
    if influencer.engagement_rate >= 0.06:
        engagement += 4
    engagement = min(95, engagement)
    sentiment = 82 if any(term in contexts.lower() for term in ("positive", "evidence-based", "helpful", "authentic")) else 70
    brand_safety_score = max(0, 100 - (risk_count * 20))

    return {
        "relevance": relevance,
        "credibility": credibility,
        "engagement": engagement,
        "sentiment": sentiment,
        "brand_safety": brand_safety_score,
        "data_source_count": max(1, len(set(influencer.citations))),
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
                followers=influencer.followers,
                engagement_rate=influencer.engagement_rate,
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
