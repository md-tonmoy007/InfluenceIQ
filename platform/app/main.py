from __future__ import annotations

import asyncio
import json
import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import settings
from app.db import Base, get_db_session
from app.models import Campaign, InfluencerResult
from app.pipeline import start_campaign_pipeline
from app.schemas import CampaignBriefPayload, CampaignCreatedResponse, CampaignResponse, InfluencerResponse
from app.service_roles import WORKER_QUEUES
from app.services import get_events, get_state, update_state

app = FastAPI(title="InfluenceIQ", version="0.1.0")

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_redis = redis.from_url(settings.REDIS_URL)
_state_redis = redis.from_url(settings.REDIS_STATE_DB)

Base.metadata.create_all(bind=_engine)


@app.get("/health")
def health() -> dict:
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
    except Exception:
        workers = {}

    return {
        "status": "ok" if db_status == "connected" and redis_status == "connected" else "degraded",
        "architecture": "multi-service",
        "queues": queue_depths,
        "workers": workers,
        "db": db_status,
        "redis": redis_status,
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
    update_state(campaign_id, status="queued", phase="queued")
    start_campaign_pipeline(campaign_id)
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
