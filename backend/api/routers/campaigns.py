from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.schemas.campaign import (
    BriefSnapshot,
    CampaignContractCreate,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from backend.api.schemas.influencer import CrawlSourceResponse, InfluencerResponse, SubScores
from backend.core.auth import decode_token, get_current_user
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

VALID_ENTRY_POINTS = {"brief_form", "discover_search", "topbar_search"}


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


def _validate_entry_point(entry_point: str | None) -> str:
    """Normalize the entry_point, defaulting to brief_form when not provided."""
    if not entry_point:
        return "brief_form"
    if entry_point not in VALID_ENTRY_POINTS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"entry_point must be one of {sorted(VALID_ENTRY_POINTS)}; "
                f"got {entry_point!r}."
            ),
        )
    return entry_point


def _serialize_brief_snapshot(snapshot: BriefSnapshot | None) -> dict[str, Any] | None:
    """Dump a BriefSnapshot to a JSON-serializable dict (or None)."""
    if snapshot is None:
        return None
    return snapshot.model_dump(exclude_none=True)


def _get_owned_campaign(
    db: Session, campaign_id: UUID, user: models.User
) -> models.Campaign:
    """Return a campaign the user may access, or raise 404."""
    campaign = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.created_by is not None and campaign.created_by != user.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _dispatch_pipeline(
    db: Session,
    db_campaign: models.Campaign,
    *,
    idempotency_key: str | None,
    owner_id: str,
) -> dict[str, Any]:
    """Initialize pipeline state and enqueue the root campaign task."""
    campaign_id_str = str(db_campaign.id)
    initialize_pipeline_state(campaign_id_str)

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
        if idempotency_key:
            clear_response(owner_id, idempotency_key)
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {exc}") from exc

    if idempotency_key:
        store_response(owner_id, idempotency_key, 200, response_body)

    return response_body


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
    entry_point = _validate_entry_point(campaign_data.entry_point)
    brief_snapshot = _serialize_brief_snapshot(campaign_data.brief_snapshot)
    is_draft = not campaign_data.start_pipeline

    db_campaign = models.Campaign(
        product=campaign_data.product,
        niche=campaign_data.industry,
        goals=campaign_data.goals,
        target_audience=campaign_data.target_audience,
        preferred_platforms=campaign_data.preferred_platforms,
        budget_range=campaign_data.budget_range,
        weights=campaign_data.weights.model_dump() if campaign_data.weights else None,
        created_by=current_user.id if current_user is not None else None,
        status="draft" if is_draft else "running",
        started_at=None if is_draft else datetime.now(UTC),
        campaign_name=campaign_data.campaign_name,
        entry_point=entry_point,
        search_query=campaign_data.search_query,
        brief_snapshot=brief_snapshot,
    )
    db.add(db_campaign)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "A campaign with this product/niche already exists for this owner. "
                "Use GET /api/campaigns/{id} to retrieve the existing campaign, "
                "or send an Idempotency-Key header to retry safely."
            ),
        ) from exc
    db.refresh(db_campaign)

    if is_draft:
        response_body = {
            "campaign_id": db_campaign.id,
            "status": db_campaign.status,
        }
        if idempotency_key:
            store_response(owner_id, idempotency_key, 200, response_body)
        return response_body

    return _dispatch_pipeline(
        db,
        db_campaign,
        idempotency_key=idempotency_key,
        owner_id=owner_id,
    )


def _enrich_campaign(
    db: Session,
    campaign: models.Campaign,
    *,
    user: models.User | None = None,
) -> dict[str, Any]:
    """Annotate a Campaign with the aggregates the listing API needs.

    The aggregates (influencer_count, top_match_score, last_activity_at)
    are computed with one small query each. They are kept on the
    response rather than the ORM model so the row's lifecycle
    columns stay read-only from the API's perspective.
    """
    response = CampaignResponse.model_validate(campaign).model_dump(mode="json")

    score_count = (
        db.query(func.count(models.InfluencerScore.id))
        .filter(models.InfluencerScore.campaign_id == campaign.id)
        .scalar()
    )
    top_score = (
        db.query(func.max(models.InfluencerScore.final_score))
        .filter(models.InfluencerScore.campaign_id == campaign.id)
        .scalar()
    )
    response["influencer_count"] = int(score_count or 0)
    response["top_match_score"] = float(top_score) if top_score is not None else None

    # Last activity: prefer the most recent score's computed_at, fall back to
    # updated_at / created_at so freshly created campaigns without scores
    # still have a meaningful timestamp.
    last_score_at = (
        db.query(func.max(models.InfluencerScore.computed_at))
        .filter(models.InfluencerScore.campaign_id == campaign.id)
        .scalar()
    )
    candidates: list[datetime] = []
    if last_score_at is not None:
        candidates.append(last_score_at)
    if campaign.updated_at is not None:
        candidates.append(campaign.updated_at)
    if campaign.completed_at is not None:
        candidates.append(campaign.completed_at)
    if campaign.started_at is not None:
        candidates.append(campaign.started_at)
    candidates.append(campaign.created_at)
    response["last_activity_at"] = max(candidates) if candidates else None

    if user is not None:
        shortlisted_count = (
            db.query(func.count(models.SavedListItem.id))
            .join(models.SavedList, models.SavedList.id == models.SavedListItem.list_id)
            .filter(
                models.SavedListItem.source_campaign_id == campaign.id,
                models.SavedList.user_id == user.id,
            )
            .scalar()
        )
        response["shortlisted_count"] = int(shortlisted_count or 0)
    else:
        response["shortlisted_count"] = 0

    contracted_count = (
        db.query(func.count(models.CampaignContract.id))
        .filter(
            models.CampaignContract.campaign_id == campaign.id,
            models.CampaignContract.status == "contracted",
        )
        .scalar()
    )
    response["contracted_count"] = int(contracted_count or 0)

    return response


@router.get("", response_model=dict[str, Any])
def list_campaigns(
    status: str | None = Query(default=None, description="Filter by campaign status"),
    entry_point: str | None = Query(default=None, description="Filter by entry_point"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """List campaigns ordered by created_at desc, with per-row aggregates.

    The response shape mirrors the single-row CampaignResponse so the
    briefs page can render a list without an extra round-trip per row.
    Status filtering accepts the same ``running`` / ``completed`` /
    ``failed`` / ``pending`` values the single campaign returns;
    ``entry_point`` filters by submission channel.
    """
    query = (
        db.query(models.Campaign)
        .filter(models.Campaign.created_by == current_user.id)
        .order_by(models.Campaign.created_at.desc())
    )
    if status:
        query = query.filter(models.Campaign.status == status)
    if entry_point:
        query = query.filter(models.Campaign.entry_point == entry_point)
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    items = [_enrich_campaign(db, row, user=current_user) for row in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{id}", response_model=dict[str, Any])
def get_campaign(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve campaign metadata along with current transient pipeline state."""
    db_campaign = _get_owned_campaign(db, id, current_user)

    campaign_id_str = str(id)
    response = _enrich_campaign(db, db_campaign, user=current_user)
    response["pipeline_state"] = get_campaign_state_payload(db_campaign, campaign_id_str)
    return response


@router.patch("/{id}", response_model=dict[str, Any])
def update_campaign(
    id: UUID,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a draft campaign's brief fields."""
    db_campaign = _get_owned_campaign(db, id, current_user)
    if db_campaign.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft campaigns can be updated.",
        )

    if payload.product is not None:
        db_campaign.product = payload.product
    if payload.industry is not None:
        db_campaign.niche = payload.industry
    if payload.goals is not None:
        db_campaign.goals = payload.goals
    if payload.target_audience is not None:
        db_campaign.target_audience = payload.target_audience
    if payload.preferred_platforms is not None:
        db_campaign.preferred_platforms = payload.preferred_platforms
    if payload.budget_range is not None:
        db_campaign.budget_range = payload.budget_range
    if payload.campaign_name is not None:
        db_campaign.campaign_name = payload.campaign_name
    if payload.brief_snapshot is not None:
        db_campaign.brief_snapshot = _serialize_brief_snapshot(payload.brief_snapshot)

    db_campaign.updated_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A campaign with this product/niche already exists for this owner.",
        ) from exc
    db.refresh(db_campaign)
    return _enrich_campaign(db, db_campaign, user=current_user)


@router.post("/{id}/submit", response_model=dict[str, Any])
def submit_campaign(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Transition a draft campaign to running and start the matching pipeline."""
    db_campaign = _get_owned_campaign(db, id, current_user)

    if db_campaign.status == "running":
        campaign_id_str = str(id)
        return {
            "campaign_id": db_campaign.id,
            "status": db_campaign.status,
            "pipeline_state": get_campaign_state_payload(db_campaign, campaign_id_str),
        }

    if db_campaign.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit a campaign with status {db_campaign.status!r}.",
        )

    db_campaign.status = "running"
    db_campaign.started_at = datetime.now(UTC)
    db_campaign.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_campaign)

    owner_id = str(current_user.id)
    return _dispatch_pipeline(db, db_campaign, idempotency_key=None, owner_id=owner_id)


@router.post("/{id}/duplicate", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def duplicate_campaign(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Clone a campaign as a new draft (brief fields only, no scores or contracts)."""
    source = _get_owned_campaign(db, id, current_user)

    copy_suffix = " (copy)"
    new_product = source.product
    if len(new_product) + len(copy_suffix) <= 255:
        new_product = f"{new_product}{copy_suffix}"

    campaign_name = source.campaign_name
    if campaign_name and len(campaign_name) + len(copy_suffix) <= 255:
        campaign_name = f"{campaign_name}{copy_suffix}"

    db_campaign = models.Campaign(
        product=new_product,
        niche=source.niche,
        goals=source.goals,
        target_audience=source.target_audience,
        preferred_platforms=source.preferred_platforms,
        budget_range=source.budget_range,
        weights=source.weights,
        created_by=current_user.id,
        status="draft",
        started_at=None,
        campaign_name=campaign_name,
        entry_point=source.entry_point,
        search_query=source.search_query,
        brief_snapshot=source.brief_snapshot,
    )
    db.add(db_campaign)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A campaign with this product/niche already exists for this owner.",
        ) from exc
    db.refresh(db_campaign)

    response = _enrich_campaign(db, db_campaign, user=current_user)
    response["campaign_id"] = db_campaign.id
    return response


@router.get("/{id}/contracts", response_model=dict[str, Any])
def list_campaign_contracts(
    id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """List outreach contract rows for a campaign."""
    _get_owned_campaign(db, id, current_user)

    query = (
        db.query(models.CampaignContract)
        .filter(models.CampaignContract.campaign_id == id)
        .order_by(models.CampaignContract.created_at.desc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    items = [
        {
            "id": str(row.id),
            "campaign_id": str(row.campaign_id),
            "influencer_id": str(row.influencer_id),
            "status": row.status,
            "notes": row.notes,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/{id}/contracts", response_model=dict[str, Any])
def upsert_campaign_contract(
    id: UUID,
    payload: CampaignContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create or update a contract row for a creator on this campaign."""
    _get_owned_campaign(db, id, current_user)

    influencer = (
        db.query(models.Influencer)
        .filter(models.Influencer.id == payload.influencer_id)
        .first()
    )
    if influencer is None:
        raise HTTPException(status_code=404, detail="Influencer not found")

    existing = (
        db.query(models.CampaignContract)
        .filter(
            models.CampaignContract.campaign_id == id,
            models.CampaignContract.influencer_id == payload.influencer_id,
        )
        .first()
    )
    if existing is not None:
        existing.status = payload.status
        existing.notes = payload.notes
        row = existing
    else:
        row = models.CampaignContract(
            campaign_id=id,
            influencer_id=payload.influencer_id,
            status=payload.status,
            notes=payload.notes,
            created_by=current_user.id,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return {
        "id": str(row.id),
        "campaign_id": str(row.campaign_id),
        "influencer_id": str(row.influencer_id),
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at,
    }


@router.delete("/{id}/contracts/{influencer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_contract(
    id: UUID,
    influencer_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Remove a contract row for a creator on this campaign."""
    _get_owned_campaign(db, id, current_user)

    row = (
        db.query(models.CampaignContract)
        .filter(
            models.CampaignContract.campaign_id == id,
            models.CampaignContract.influencer_id == influencer_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{id}/state", response_model=dict[str, Any])
def get_campaign_state(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve execution progress, falling back to the durable campaign lifecycle state.

    The response is augmented with ``last_event_id`` derived from the
    Redis event counter so a WebSocket client that just opened the
    connection can pass ``?last_event_id=N`` and receive only the
    events it has not yet seen.
    """
    db_campaign = _get_owned_campaign(db, id, current_user)
    payload = get_campaign_state_payload(db_campaign, str(id))
    payload["last_event_id"] = _get_last_event_id(str(id))
    return payload


@router.get("/{id}/facets", response_model=dict[str, Any])
def get_campaign_facets(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return facet counts for the Discover filter rail of a campaign.

    Counts come from the influencers scored for this campaign grouped
    by platform, trust grade (derived from final_score), primary
    category, primary location, and follower tier (derived from
    follower_count buckets). Missing values are reported under
    ``"unknown"`` so the UI can show "no data" rather than dropping
    the bucket.
    """
    _get_owned_campaign(db, id, current_user)

    rows = (
        db.query(
            models.InfluencerScore.final_score,
            models.InfluencerScore.data_source_count,
            models.Influencer.platforms,
            models.Influencer.primary_platform,
            models.Influencer.primary_category,
            models.Influencer.primary_location,
            models.Influencer.follower_count,
        )
        .join(models.Influencer, models.Influencer.id == models.InfluencerScore.influencer_id)
        .filter(models.InfluencerScore.campaign_id == id)
        .all()
    )

    def _bucket_grade(score: float | None) -> str:
        if score is None:
            return "unknown"
        if score >= 90:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        return "D"

    def _bucket_tier(followers: int | None) -> str:
        if followers is None:
            return "unknown"
        if followers >= 1_000_000:
            return "mega"
        if followers >= 500_000:
            return "premium"
        if followers >= 100_000:
            return "established"
        if followers >= 25_000:
            return "mid"
        if followers >= 10_000:
            return "rising"
        return "nano"

    def _bucket(value: str | None) -> str:
        return value if value else "unknown"

    platform_counts: dict[str, int] = {}
    grade_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    location_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}

    for final_score, _ds_count, platforms, primary_platform, category, location, followers in rows:
        # Platform facet: prefer primary_platform when present, otherwise
        # fall back to the keys in the platforms JSON dict (lowercased).
        platform_key: str | None = None
        if primary_platform:
            platform_key = primary_platform.lower()
        elif isinstance(platforms, dict) and platforms:
            platform_key = next(iter(platforms.keys()), None)
        platform_counts[_bucket(platform_key)] = platform_counts.get(_bucket(platform_key), 0) + 1

        grade = _bucket_grade(final_score)
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

        category_counts[_bucket(category)] = category_counts.get(_bucket(category), 0) + 1
        location_counts[_bucket(location)] = location_counts.get(_bucket(location), 0) + 1
        tier_counts[_bucket_tier(followers)] = tier_counts.get(_bucket_tier(followers), 0) + 1

    def _to_facet(counts: dict[str, int]) -> list[dict[str, Any]]:
        return [
            {"value": value, "count": count}
            for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    return {
        "campaign_id": str(id),
        "platforms": _to_facet(platform_counts),
        "trust_grades": _to_facet(grade_counts),
        "categories": _to_facet(category_counts),
        "locations": _to_facet(location_counts),
        "follower_tiers": _to_facet(tier_counts),
        "total": len(rows),
    }


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
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve ranked influencers for a campaign with durable provenance details.

    Returns ``{"items": [...], "next_cursor": "..."|"None", "limit": int}``.
    Ordering is ``final_score DESC, data_source_count DESC, influencer_id``;
    the cursor encodes the tie-breaker key so successive pages are stable
    even when new InfluencerScore rows land mid-pagination.
    """
    _get_owned_campaign(db, id, current_user)

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
            _to_influencer_response(inf, score, sources_response)
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


def _to_influencer_response(
    inf: models.Influencer,
    score: models.InfluencerScore,
    sources: list[CrawlSourceResponse],
) -> InfluencerResponse:
    """Map (Influencer, InfluencerScore) to a frontend-ready InfluencerResponse.

    Adds the best-effort follower / engagement / rate metrics that the
    rest of the workspace shell needs. Missing values stay ``None``
    (rendered as "—" on the frontend) instead of fabricated zeros.
    """
    return InfluencerResponse(
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
        sources=sources,
        primary_platform=inf.primary_platform,
        primary_handle=inf.primary_handle,
        follower_count=inf.follower_count,
        engagement_rate=inf.engagement_rate,
        avg_views=inf.avg_views,
        primary_category=inf.primary_category,
        primary_location=inf.primary_location,
    )


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
