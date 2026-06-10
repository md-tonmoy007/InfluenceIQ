from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Literal
import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import case, create_engine, inspect, text
from sqlalchemy.orm import Session
import structlog

from app.auth import (
    authenticate_token,
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    hash_password,
    normalize_email,
    set_auth_cookie,
    verify_password,
)
from app.celery_app import celery_app
from app.config import settings
<<<<<<< HEAD
from app.db import Base, SessionLocal, get_db_session
from app.logging_config import bind_campaign, clear_log_context, configure_logging
from app.models import Campaign, InfluencerResult, User
from app.pipeline import start_campaign_pipeline
from app.schemas import (
    AuthResponse,
    CampaignBriefPayload,
    CampaignCreatedResponse,
    CampaignResponse,
    InfluencerListResponse,
    InfluencerResponse,
    LoginRequest,
    SignupRequest,
    UserResponse,
)
=======
>>>>>>> b637425645e09d6e2c66685faf54dbcdda62a393
from app.service_roles import WORKER_QUEUES

app = FastAPI(title="InfluenceIQ", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_redis = redis.from_url(settings.REDIS_URL)


def _ensure_auth_schema() -> None:
    inspector = inspect(_engine)
    if not inspector.has_table("campaigns"):
        return

    campaign_columns = {column["name"] for column in inspector.get_columns("campaigns")}
    statements: list[str] = []
    if "owner_user_id" not in campaign_columns:
        if _engine.dialect.name == "postgresql":
            statements.append("ALTER TABLE campaigns ADD COLUMN owner_user_id UUID NULL")
        else:
            statements.append("ALTER TABLE campaigns ADD COLUMN owner_user_id CHAR(32) NULL")
    if _engine.dialect.name == "postgresql":
        statements.append("CREATE INDEX IF NOT EXISTS ix_campaigns_owner_user_id ON campaigns (owner_user_id)")

    if not statements:
        return
    with _engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


_ensure_auth_schema()


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
<<<<<<< HEAD


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(
    payload: SignupRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> AuthResponse:
    email = _validated_email(payload.email)
    existing = session.query(User).filter(User.email == email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        company_name=payload.company_name.strip(),
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    set_auth_cookie(response, create_access_token(user))
    return AuthResponse(user=_user_response(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> AuthResponse:
    email = normalize_email(payload.email)
    user = session.query(User).filter(User.email == email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    set_auth_cookie(response, create_access_token(user))
    return AuthResponse(user=_user_response(user))


@app.post("/api/auth/logout")
def logout(response: Response) -> dict:
    clear_auth_cookie(response)
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)


@app.post("/api/campaigns", response_model=CampaignCreatedResponse)
def create_campaign(
    payload: CampaignBriefPayload,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CampaignCreatedResponse:
    campaign = Campaign(
        owner_user_id=current_user.user_id,
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
def get_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> CampaignResponse:
    campaign_uuid = _campaign_uuid(campaign_id)
    campaign = _owned_campaign(session, campaign_uuid, current_user)

    state_payload = _campaign_state_payload(session, campaign_uuid, campaign.status)
    influencer_count = state_payload["influencer_count"]
    return CampaignResponse(
        campaign_id=str(campaign.campaign_id),
        brand=campaign.brand,
        product=campaign.product,
        category=campaign.category,
        goal=campaign.goal,
        status=campaign.status,
        created_at=campaign.created_at,
        payload=campaign.payload,
        pipeline_state=state_payload,
        influencer_count=influencer_count,
        partial_results_available=bool(state_payload["partial_results_available"]),
        error=state_payload.get("error") or None,
    )


@app.get("/api/campaigns/{campaign_id}/state")
def get_campaign_state(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> dict:
    campaign_uuid = _campaign_uuid(campaign_id)
    campaign = _owned_campaign(session, campaign_uuid, current_user)
    return _campaign_state_payload(session, campaign_uuid, campaign.status)


@app.get("/api/campaigns/{campaign_id}/influencers", response_model=InfluencerListResponse)
def get_campaign_influencers(
    campaign_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    platform: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    min_followers: int | None = Query(default=None, ge=0),
    max_followers: int | None = Query(default=None, ge=0),
    sort_by: Literal["match_score", "trust_grade", "engagement_rate", "followers", "name", "created_at"] = Query(
        default="match_score"
    ),
    sort_dir: Literal["asc", "desc"] = Query(default="desc"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> InfluencerListResponse:
    campaign_uuid = _campaign_uuid(campaign_id)
    _owned_campaign(session, campaign_uuid, current_user)

    query = session.query(InfluencerResult).filter(InfluencerResult.campaign_id == campaign_uuid)
    applied_filters: dict[str, str | int] = {}

    if platform:
        applied_filters["platform"] = platform
        query = query.filter(InfluencerResult.platform.ilike(platform))
    if grade:
        applied_filters["grade"] = grade
        query = query.filter(InfluencerResult.trust_grade == grade)
    if min_followers is not None:
        applied_filters["min_followers"] = min_followers
        query = query.filter(InfluencerResult.followers >= min_followers)
    if max_followers is not None:
        applied_filters["max_followers"] = max_followers
        query = query.filter(InfluencerResult.followers <= max_followers)

    total = query.count()
    order_column = _influencer_sort_column(sort_by)
    ordering = order_column.asc() if sort_dir == "asc" else order_column.desc()
    rows = (
        query.order_by(ordering, InfluencerResult.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return InfluencerListResponse(
        items=[
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
        ],
        total=total,
        limit=limit,
        offset=offset,
        filters=applied_filters,
        sort={"by": sort_by, "direction": sort_dir},
    )


@app.websocket("/ws/campaign/{campaign_id}")
async def campaign_websocket(
    websocket: WebSocket,
    campaign_id: str,
    last_event_id: int = Query(default=0, ge=0),
) -> None:
    session = SessionLocal()
    try:
        try:
            campaign_uuid = uuid.UUID(campaign_id)
            current_user = authenticate_token(session, websocket.cookies.get(settings.AUTH_COOKIE_NAME))
        except (HTTPException, ValueError):
            await websocket.close(code=1008)
            return

        campaign = session.get(Campaign, campaign_uuid)
        if campaign is None or campaign.owner_user_id != current_user.user_id:
            await websocket.close(code=1008)
            return
    finally:
        session.close()

    await websocket.accept()

    replay_events = get_events(campaign_id, after_event_id=last_event_id)
    for event in replay_events:
        await websocket.send_json(event)

    pubsub = _state_redis.pubsub()
    pubsub.subscribe(f"campaign:{campaign_id}")
    last_heartbeat_at = datetime.now(UTC)
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                last_heartbeat_at = datetime.now(UTC)
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    await websocket.send_json(json.loads(str(data)))
                except json.JSONDecodeError:
                    await websocket.send_text(str(data))
            else:
                now = datetime.now(UTC)
                if (now - last_heartbeat_at).total_seconds() >= 15:
                    last_heartbeat_at = now
                    await websocket.send_json(
                        {
                            "event_id": 0,
                            "type": "heartbeat",
                            "campaign_id": campaign_id,
                            "timestamp": now.isoformat(),
                            "payload": {"state": get_state(campaign_id)},
                        }
                    )
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


def _validated_email(email: str) -> str:
    normalized = normalize_email(email)
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    return normalized


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        user_id=str(user.user_id),
        company_name=user.company_name,
        name=user.name,
        email=user.email,
    )


def _owned_campaign(session: Session, campaign_uuid: uuid.UUID, user: User) -> Campaign:
    campaign = session.get(Campaign, campaign_uuid)
    if campaign is None or campaign.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _campaign_influencer_count(session: Session, campaign_uuid: uuid.UUID) -> int:
    return session.query(InfluencerResult).filter(InfluencerResult.campaign_id == campaign_uuid).count()


def _campaign_state_payload(session: Session, campaign_uuid: uuid.UUID, campaign_status: str) -> dict:
    state = get_state(str(campaign_uuid))
    influencer_count = _campaign_influencer_count(session, campaign_uuid)
    payload = {
        "campaign_id": str(campaign_uuid),
        "status": state.get("status") or campaign_status,
        "phase": state.get("phase") or campaign_status,
        **state,
        "influencer_count": influencer_count,
        "partial_results_available": influencer_count > 0,
    }
    return payload


def _influencer_sort_column(sort_by: str):
    if sort_by == "trust_grade":
        return case(
            (InfluencerResult.trust_grade == "A+", 5),
            (InfluencerResult.trust_grade == "A", 4),
            (InfluencerResult.trust_grade == "B", 3),
            (InfluencerResult.trust_grade == "C", 2),
            else_=1,
        )
    return {
        "match_score": InfluencerResult.match_score,
        "engagement_rate": InfluencerResult.engagement_rate,
        "followers": InfluencerResult.followers,
        "name": InfluencerResult.name,
        "created_at": InfluencerResult.created_at,
    }[sort_by]
=======
>>>>>>> b637425645e09d6e2c66685faf54dbcdda62a393
