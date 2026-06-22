from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.schemas.campaign import CampaignCreate, CampaignResponse
from backend.api.schemas.influencer import CrawlSourceResponse, InfluencerResponse, SubScores
from backend.core.auth import decode_token
from backend.core.cache.idempotency import (
    clear_response,
    get_stored_response,
    store_response,
)
from backend.core.cache.pipeline_state import (
    get_pipeline_state,
    initialize_pipeline_state,
)
from backend.core.database import models
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

_optional_oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user_optional(
    token: str | None = Depends(_optional_oauth),
    access_token: str | None = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
) -> models.User | None:
    """Like :func:`backend.core.auth.get_current_user` but returns ``None`` when
    no credential is supplied, instead of raising 401.

    Lets the ``POST /api/campaigns`` endpoint stay open for the demo
    seed path and unauthenticated clients while still wiring up
    ownership whenever a real token is present.
    """
    raw_token = token or access_token
    if not raw_token:
        return None
    try:
        payload = decode_token(raw_token)
    except HTTPException:
        return None
    if payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return None
    return db.query(models.User).filter(models.User.id == user_uuid).first()


@router.post("", response_model=dict[str, Any])
def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: models.User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Create a campaign, initialize transient state, and dispatch the pipeline.

    The endpoint is idempotent at two layers:

    1. **HTTP** — an ``Idempotency-Key`` header caches the response in
       Redis for 1 hour; the same key + same owner returns the cached
       body instead of creating a second campaign.
    2. **Database** — a ``UNIQUE(created_by, product, niche)`` constraint
       rejects a duplicate natural key with HTTP 409, even if the
       client forgot the header.

    ``current_user`` is optional so the demo seed path and unauthenticated
    ``POST`` calls still work; when present, the campaign is owned by
    that user and org-scoping kicks in.
    """
    owner_id = str(current_user.id) if current_user is not None else "anonymous"

    # 1. Idempotency-Key fast path --------------------------------------------------
    if idempotency_key:
        cached = get_stored_response(owner_id, idempotency_key)
        if cached is not None:
            return cached["body"]

    # 2. Build + insert ------------------------------------------------------------
    db_campaign = models.Campaign(
        product=campaign_data.product,
        niche=campaign_data.industry,
        goals=campaign_data.goals,
        target_audience=campaign_data.target_audience,
        preferred_platforms=campaign_data.preferred_platforms,
        budget_range=campaign_data.budget_range,
        weights=campaign_data.weights.model_dump() if campaign_data.weights else None,
        created_by=current_user.id if current_user is not None else None,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(db_campaign)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Natural-key collision: another campaign with the same
        # (created_by, product, niche) already exists. Surface a
        # structured 409 so the client can decide whether to fetch
        # the existing row.
        raise HTTPException(
            status_code=409,
            detail=(
                "A campaign with this product/niche already exists for this owner. "
                "Use GET /api/campaigns/{id} to retrieve the existing campaign, "
                "or send an Idempotency-Key header to retry safely."
            ),
        ) from exc
    db.refresh(db_campaign)

    campaign_id_str = str(db_campaign.id)
    initialize_pipeline_state(campaign_id_str)

    # 3. Dispatch pipeline (post-commit) ------------------------------------------
    response_body: dict[str, Any] = {
        "campaign_id": db_campaign.id,
        "status": db_campaign.status,
        "pipeline_state": get_campaign_state_payload(db_campaign, campaign_id_str),
    }

    try:
        from backend.pipeline.tasks import start_campaign

        start_campaign(campaign_id_str)
    except Exception as exc:
        db_campaign.status = "failed"
        db_campaign.failed_at = datetime.now(UTC)
        db_campaign.failure_reason = str(exc)
        db.commit()
        # The campaign row was created; do not cache this as a
        # successful idempotent response because the pipeline never
        # started. The client can retry with the same key.
        if idempotency_key:
            clear_response(owner_id, idempotency_key)
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {exc}") from exc

    # 4. Cache successful response for Idempotency-Key retries --------------------
    if idempotency_key:
        store_response(owner_id, idempotency_key, 200, response_body)

    return response_body


@router.get("/{id}", response_model=dict[str, Any])
def get_campaign(id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve campaign metadata along with current transient pipeline state."""
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign_id_str = str(id)
    return {
        "campaign": CampaignResponse.model_validate(db_campaign),
        "pipeline_state": get_campaign_state_payload(db_campaign, campaign_id_str),
    }


@router.get("/{id}/state", response_model=dict[str, Any])
def get_campaign_state(id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve execution progress, falling back to the durable campaign lifecycle state.

    The response is augmented with ``last_event_id`` derived from the
    Redis event counter so a WebSocket client that just opened the
    connection can pass ``?last_event_id=N`` and receive only the
    events it has not yet seen.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    payload = get_campaign_state_payload(db_campaign, str(id))
    payload["last_event_id"] = _get_last_event_id(str(id))
    return payload


def _get_last_event_id(campaign_id_str: str) -> int:
    """Return the highest event_id emitted so far for ``campaign_id``.

    Reads the event-id counter that :func:`backend.core.cache.event_log.emit_event`
    maintains alongside the replay list. Returns 0 when the counter is
    not present (e.g. campaign was created but no task has emitted yet).
    """
    try:
        from backend.core.cache.event_log import EVENT_COUNTER_PREFIX
        from backend.core.cache.redis_client import redis_client

        counter_key = f"{EVENT_COUNTER_PREFIX}{campaign_id_str}"
        raw = redis_client.get(counter_key)
        return int(raw) if raw else 0
    except Exception:
        return 0


@router.get("/{id}/influencers", response_model=dict[str, Any])
def get_campaign_influencers(
    id: UUID,
    platform: str | None = Query(default=None, description="Filter by platform handle availability"),
    grade: str | None = Query(default=None, description="Filter by trust grade, e.g. 'A+', 'A'"),
    niche: str | None = Query(default=None, description="Filter by core niche"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(
        default=None,
        description=(
            "Opaque pagination cursor returned in the previous response's "
            "`next_cursor` field. Preferred over `offset` for stable ranking "
            "across writes."
        ),
    ),
    offset: int = Query(default=0, ge=0, description="Pagination offset (legacy; prefer cursor)"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve ranked influencers for a campaign with durable provenance details.

    Returns ``{"items": [...], "next_cursor": "..."|"None", "limit": int}``.
    Ordering is ``final_score DESC, data_source_count DESC, influencer_id``;
    the cursor encodes the tie-breaker key so successive pages are stable
    even when new InfluencerScore rows land mid-pagination.
    """
    db_campaign = db.query(models.Campaign).filter(models.Campaign.id == id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = (
        db.query(models.InfluencerScore, models.Influencer)
        .join(models.Influencer, models.InfluencerScore.influencer_id == models.Influencer.id)
        .filter(models.InfluencerScore.campaign_id == id)
    )

    if platform:
        query = query.filter(models.Influencer.platforms.has_key(platform.lower()))
    if niche:
        query = query.filter(models.Influencer.canonical_name.ilike(f"%{niche}%"))
    if grade:
        grade_bounds = {
            "A+": (90.0, 100.0),
            "A": (80.0, 89.99),
            "B": (70.0, 79.99),
            "C": (60.0, 69.99),
            "D": (0.0, 59.99),
        }
        bounds = grade_bounds.get(grade.upper())
        if bounds:
            query = query.filter(
                models.InfluencerScore.final_score >= bounds[0],
                models.InfluencerScore.final_score <= bounds[1],
            )

    # Stable ordering: final_score DESC, data_source_count DESC, influencer_id ASC.
    query = query.order_by(
        models.InfluencerScore.final_score.desc(),
        models.InfluencerScore.data_source_count.desc(),
        models.InfluencerScore.influencer_id.asc(),
    )

    # Cursor takes precedence over offset when both are provided.
    if cursor:
        cursor_decoded = _decode_cursor(cursor)
        if cursor_decoded is None:
            raise HTTPException(status_code=400, detail="Invalid cursor")
        cursor_score, cursor_id = cursor_decoded
        # Pagination keyset: rows strictly after (cursor_score, cursor_id).
        query = query.filter(
            (models.InfluencerScore.final_score < cursor_score)
            | (
                (models.InfluencerScore.final_score == cursor_score)
                & (models.InfluencerScore.influencer_id > cursor_id)
            )
        )
    else:
        query = query.offset(offset)

    # Fetch one extra row so we can decide if there's a next page.
    rows = query.limit(limit + 1).all()
    has_more = len(rows) > limit
    page_rows = rows[:limit]

    response_list = []
    last_score_row: tuple[float, Any] | None = None
    for score, inf in page_rows:
        sources_response = _campaign_influencer_sources(db, id, inf.id)
        response_list.append(
            InfluencerResponse(
                influencer_id=inf.id,
                canonical_name=inf.canonical_name,
                platforms=inf.platforms or {},
                credentials=inf.credentials or [],
                mentions=inf.mentions or [],
                final_score=score.final_score,
                sub_scores=SubScores(
                    relevance=score.relevance_score,
                    credibility=score.credibility_score,
                    engagement=score.engagement_score,
                    sentiment=score.sentiment_score,
                    brand_safety=score.brand_safety_score,
                ),
                confidence=score.confidence_level,
                data_source_count=score.data_source_count,
                score_version=score.score_version,
                computed_at=score.computed_at,
                signal_scores=score.signal_scores or {},
                risk_category=score.risk_category,
                detection_category=score.detection_category,
                positive_reasons=score.positive_reasons or [],
                negative_reasons=score.negative_reasons or [],
                sources=sources_response,
            )
        )
        last_score_row = (score.final_score, inf.id)

    next_cursor: str | None = None
    if has_more and last_score_row is not None:
        next_cursor = _encode_cursor(last_score_row[0], str(last_score_row[1]))

    return {
        "items": response_list,
        "next_cursor": next_cursor,
        "limit": limit,
    }


def _encode_cursor(final_score: float, influencer_id: str) -> str:
    """Encode a (final_score, influencer_id) keyset cursor.

    Cursor format (URL-safe base64 of a JSON object) — opaque to
    clients; clients should treat it as a string.
    """
    raw = json.dumps({"s": final_score, "i": influencer_id}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_cursor(cursor: str) -> tuple[float, str] | None:
    """Decode a cursor produced by :func:`_encode_cursor`.

    Returns ``None`` on malformed input (the caller surfaces a 400).
    """
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        parsed = json.loads(raw.decode("utf-8"))
        return float(parsed["s"]), str(parsed["i"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def get_campaign_state_payload(campaign: models.Campaign, campaign_id_str: str) -> dict[str, Any]:
    state = get_pipeline_state(campaign_id_str)
    if state:
        state.setdefault("status", campaign.status)
        state.setdefault("started_at", campaign.started_at.isoformat() if campaign.started_at else None)
        return state
    return {
        "campaign_id": campaign_id_str,
        "status": campaign.status,
        "phase": campaign.status,
        "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
        "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
        "failed_at": campaign.failed_at.isoformat() if campaign.failed_at else None,
        "failure_reason": campaign.failure_reason,
        "message": "Redis state unavailable; returning durable campaign lifecycle state.",
    }


def _campaign_influencer_sources(db: Session, campaign_id: UUID, influencer_id: UUID) -> list[CrawlSourceResponse]:
    links = (
        db.query(models.CrawlSourceInfluencer, models.CrawlSource)
        .join(models.CrawlSource, models.CrawlSource.id == models.CrawlSourceInfluencer.crawl_source_id)
        .filter(
            models.CrawlSource.campaign_id == campaign_id,
            models.CrawlSourceInfluencer.influencer_id == influencer_id,
        )
        .all()
    )
    if links:
        return [
            CrawlSourceResponse(
                url=source.url,
                title=source.title,
                relevance_score=source.relevance_score,
                status=source.status,
                mention_id=link.mention_id,
                mention=link.mention,
            )
            for link, source in links
        ]

    legacy_sources = (
        db.query(models.CrawlSource)
        .filter(
            models.CrawlSource.campaign_id == campaign_id,
            models.CrawlSource.influencer_id == influencer_id,
        )
        .all()
    )
    return [
        CrawlSourceResponse(
            url=src.url,
            title=src.title,
            relevance_score=src.relevance_score,
            status=src.status,
        )
        for src in legacy_sources
    ]
