from __future__ import annotations

import asyncio
import json
from collections import Counter
import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import structlog

from app.celery_app import celery_app
from app.config import settings
from app.db import Base, get_db_session
from app.logging_config import bind_campaign, clear_log_context, configure_logging
from app.models import Campaign, InfluencerResult
from app.pipeline import start_campaign_pipeline
from app.schemas import CampaignBriefPayload, CampaignCreatedResponse, CampaignResponse, InfluencerResponse
from app.service_roles import WORKER_QUEUES
from app.services import get_events, get_state, update_state

configure_logging(settings.LOG_LEVEL)

app = FastAPI(title="InfluenceIQ", version="0.1.0")
logger = structlog.get_logger(__name__)

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_redis = redis.from_url(settings.REDIS_URL)
_state_redis = redis.from_url(settings.REDIS_STATE_DB)
_result_redis = redis.from_url(settings.CELERY_RESULT_BACKEND)

Base.metadata.create_all(bind=_engine)


@app.get("/health")
def health() -> dict:
    runtime = _runtime_status()
    return {
        "status": "ok" if runtime["db"] == "connected" and runtime["redis"] == "connected" else "degraded",
        "architecture": "multi-service",
        "queues": runtime["queues"],
        "workers": runtime["workers"],
        "db": runtime["db"],
        "redis": runtime["redis"],
    }


@app.get("/ready")
def ready() -> JSONResponse:
    runtime = _runtime_status()
    ready_status = runtime["db"] == "connected" and runtime["redis"] == "connected" and not runtime["missing_queues"]
    payload = {
        "status": "ready" if ready_status else "not_ready",
        "architecture": "multi-service",
        **runtime,
    }
    return JSONResponse(payload, status_code=200 if ready_status else 503)


@app.get("/ops/queues")
def queue_observability() -> JSONResponse:
    runtime = _runtime_status()
    celery_runtime = _celery_runtime(runtime["worker_queues"])
    result_summary = _celery_result_summary()

    queues = {
        queue_name: {
            "depth": runtime["queues"].get(queue_name),
            "workers": [
                worker_name
                for worker_name, queue_names in runtime["worker_queues"].items()
                if queue_name in queue_names
            ],
            "active_tasks": celery_runtime["active_by_queue"].get(queue_name, 0),
            "reserved_tasks": celery_runtime["reserved_by_queue"].get(queue_name, 0),
            "scheduled_tasks": celery_runtime["scheduled_by_queue"].get(queue_name, 0),
        }
        for queue_name in WORKER_QUEUES
    }
    status = (
        "ok"
        if runtime["db"] == "connected" and runtime["redis"] == "connected" and not runtime["missing_queues"]
        else "degraded"
    )
    payload = {
        "status": status,
        "queues": queues,
        "workers": celery_runtime["workers"],
        "missing_queues": runtime["missing_queues"],
        "task_events_enabled": True,
        "result_backend": result_summary,
    }
    return JSONResponse(payload, status_code=200 if status == "ok" else 503)


def _runtime_status() -> dict:
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "down"

    try:
        _redis.ping()
        queue_depths = {queue_name: _redis.llen(queue_name) for queue_name in WORKER_QUEUES}
        redis_status = "connected"
    except Exception:
        queue_depths = {queue_name: None for queue_name in WORKER_QUEUES}
        redis_status = "down"

    try:
        inspect = celery_app.control.inspect(timeout=1)
        active = inspect.active() or {}
        workers = {name: len(tasks) for name, tasks in active.items()}
        active_queues = inspect.active_queues() or {}
    except Exception:
        workers = {}
        active_queues = {}

    queues_by_worker = {
        worker_name: sorted(queue.get("name", "") for queue in queues if queue.get("name"))
        for worker_name, queues in active_queues.items()
    }
    queues_by_worker = _with_inferred_worker_queues(queues_by_worker, workers)
    covered_queues = sorted({queue for queues in queues_by_worker.values() for queue in queues})
    missing_queues = sorted(set(WORKER_QUEUES) - set(covered_queues))
    return {
        "queues": queue_depths,
        "workers": workers,
        "worker_queues": queues_by_worker,
        "expected_queues": WORKER_QUEUES,
        "missing_queues": missing_queues,
        "db": db_status,
        "redis": redis_status,
    }


def _with_inferred_worker_queues(queues_by_worker: dict[str, list[str]], workers: dict[str, int]) -> dict[str, list[str]]:
    inferred = dict(queues_by_worker)
    worker_queue_by_prefix = {
        "search@": "search_queue",
        "crawl@": "crawl_queue",
        "extract@": "extract_queue",
        "score@": "score_queue",
    }
    for worker_name in workers:
        if inferred.get(worker_name):
            continue
        for prefix, queue_name in worker_queue_by_prefix.items():
            if worker_name.startswith(prefix):
                inferred[worker_name] = [queue_name]
                break
    return inferred


def _celery_runtime(queue_fallback: dict[str, list[str]] | None = None) -> dict:
    empty = {
        "workers": {},
        "active_by_queue": {},
        "reserved_by_queue": {},
        "scheduled_by_queue": {},
    }
    try:
        inspect = celery_app.control.inspect(timeout=1)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        stats = inspect.stats() or {}
        active_queues = inspect.active_queues() or {}
    except Exception as exc:
        logger.warning("celery_observability_failed", error=str(exc))
        return empty

    queues_by_worker = {
        worker_name: sorted(queue.get("name", "") for queue in queues if queue.get("name"))
        for worker_name, queues in active_queues.items()
    }
    if queue_fallback:
        queues_by_worker = {**queue_fallback, **{name: queues for name, queues in queues_by_worker.items() if queues}}
    active_by_queue = _count_tasks_by_queue(active, queues_by_worker)
    reserved_by_queue = _count_tasks_by_queue(reserved, queues_by_worker)
    scheduled_by_queue = _count_scheduled_tasks_by_queue(scheduled, queues_by_worker)
    workers = {
        worker_name: {
            "online": True,
            "queues": queues_by_worker.get(worker_name, []),
            "active_tasks": len(active.get(worker_name, [])),
            "reserved_tasks": len(reserved.get(worker_name, [])),
            "scheduled_tasks": len(scheduled.get(worker_name, [])),
            "total_tasks": stats.get(worker_name, {}).get("total", {}),
        }
        for worker_name in sorted(set(active) | set(reserved) | set(scheduled) | set(queues_by_worker))
    }

    return {
        "workers": workers,
        "active_by_queue": active_by_queue,
        "reserved_by_queue": reserved_by_queue,
        "scheduled_by_queue": scheduled_by_queue,
    }


def _count_tasks_by_queue(tasks_by_worker: dict, queues_by_worker: dict[str, list[str]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for worker_name, tasks in tasks_by_worker.items():
        queue_name = _worker_primary_queue(worker_name, queues_by_worker)
        counts[queue_name] += len(tasks)
    return dict(counts)


def _count_scheduled_tasks_by_queue(tasks_by_worker: dict, queues_by_worker: dict[str, list[str]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for worker_name, entries in tasks_by_worker.items():
        queue_name = _worker_primary_queue(worker_name, queues_by_worker)
        counts[queue_name] += len(entries)
    return dict(counts)


def _worker_primary_queue(worker_name: str, queues_by_worker: dict[str, list[str]]) -> str:
    queues = queues_by_worker.get(worker_name, [])
    return queues[0] if queues else "unknown"


def _celery_result_summary(limit: int = 10) -> dict:
    try:
        status_counts: Counter[str] = Counter()
        failed: list[dict] = []
        total_seen = 0
        for raw_key in _result_redis.scan_iter(match="celery-task-meta-*", count=100):
            total_seen += 1
            raw_value = _result_redis.get(raw_key)
            if raw_value is None:
                continue
            payload = json.loads(raw_value.decode() if isinstance(raw_value, bytes) else str(raw_value))
            status = str(payload.get("status", "UNKNOWN"))
            status_counts[status] += 1
            if status == "FAILURE" and len(failed) < limit:
                task_id = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
                failed.append(
                    {
                        "task_id": task_id.replace("celery-task-meta-", "", 1),
                        "result": str(payload.get("result", ""))[:300],
                        "traceback": str(payload.get("traceback", ""))[:500],
                    }
                )
        return {
            "connected": True,
            "total_results_seen": total_seen,
            "status_counts": dict(status_counts),
            "failed_count": status_counts.get("FAILURE", 0),
            "recent_failures": failed,
        }
    except Exception as exc:
        logger.warning("celery_result_backend_observability_failed", error=str(exc))
        return {
            "connected": False,
            "total_results_seen": 0,
            "status_counts": {},
            "failed_count": None,
            "recent_failures": [],
            "error": str(exc),
        }


@app.get("/")
def root() -> dict:
    return {
        "service": "backend-core",
        "project": "InfluenceIQ",
        "version": app.version,
        "worker_queues": WORKER_QUEUES,
    }


@app.post("/api/campaigns", response_model=CampaignCreatedResponse)
def create_campaign(
    payload: CampaignBriefPayload,
    session: Session = Depends(get_db_session),
) -> CampaignCreatedResponse:
    campaign = Campaign(
        brand=payload.brand,
        product=payload.product,
        category=payload.category,
        goal=payload.goal,
        payload=payload.model_dump(),
        status="queued",
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    campaign_id = str(campaign.campaign_id)
    bind_campaign(campaign_id, brand=campaign.brand, product=campaign.product)
    try:
        logger.info("campaign_created", status="queued")
        update_state(campaign_id, status="queued", phase="queued")
        start_campaign_pipeline(campaign_id)
        logger.info("campaign_pipeline_triggered")
    finally:
        clear_log_context()
    return CampaignCreatedResponse(campaign_id=campaign_id, status="queued")


@app.get("/api/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, session: Session = Depends(get_db_session)) -> CampaignResponse:
    campaign = session.get(Campaign, _campaign_uuid(campaign_id))
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse(
        campaign_id=str(campaign.campaign_id),
        brand=campaign.brand,
        product=campaign.product,
        category=campaign.category,
        goal=campaign.goal,
        status=campaign.status,
        created_at=campaign.created_at,
        payload=campaign.payload,
        pipeline_state=get_state(campaign_id),
    )


@app.get("/api/campaigns/{campaign_id}/state")
def get_campaign_state(campaign_id: str, session: Session = Depends(get_db_session)) -> dict:
    if session.get(Campaign, _campaign_uuid(campaign_id)) is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return get_state(campaign_id)


@app.get("/api/campaigns/{campaign_id}/influencers", response_model=list[InfluencerResponse])
def get_campaign_influencers(
    campaign_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[InfluencerResponse]:
    if session.get(Campaign, _campaign_uuid(campaign_id)) is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    rows = (
        session.query(InfluencerResult)
        .filter(InfluencerResult.campaign_id == _campaign_uuid(campaign_id))
        .order_by(InfluencerResult.match_score.desc(), InfluencerResult.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        InfluencerResponse(
            id=row.influencer_id,
            name=row.name,
            handle=row.handle,
            platform=row.platform,
            followers=row.followers,
            engagementRate=round(row.engagement_rate, 2),
            matchScore=round(row.match_score, 2),
            trustGrade=row.trust_grade,
            brandSafetyFlags=row.brand_safety_flags or [],
            citations=row.citations or [],
            rate=row.rate,
            sub_scores=row.sub_scores or {},
            score_payload=row.score_payload or {},
            source_payload=row.source_payload or {},
        )
        for row in rows
    ]


@app.websocket("/ws/campaign/{campaign_id}")
async def campaign_websocket(
    websocket: WebSocket,
    campaign_id: str,
    last_event_id: int = Query(default=0, ge=0),
) -> None:
    await websocket.accept()

    replay_events = get_events(campaign_id, after_event_id=last_event_id)
    for event in replay_events:
        await websocket.send_json(event)

    pubsub = _state_redis.pubsub()
    pubsub.subscribe(f"campaign:{campaign_id}")
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    await websocket.send_json(json.loads(str(data)))
                except json.JSONDecodeError:
                    await websocket.send_text(str(data))
            else:
                await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.unsubscribe(f"campaign:{campaign_id}")
        pubsub.close()


def _campaign_uuid(campaign_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Campaign not found") from exc
