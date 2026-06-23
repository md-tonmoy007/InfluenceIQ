"""Saved-lists router — user-curated collections of influencers.

Replaces the hard-coded /data/lists.ts demo data. Each list belongs to
exactly one user, and items join influencers (and optionally the
campaign the creator was added from) with a match-score snapshot.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import models
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/lists", tags=["lists"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    status: str = Field(default="active", pattern="^(active|draft)$")


class ListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|draft)$")


class ListItemCreate(BaseModel):
    influencer_id: uuid.UUID
    source_campaign_id: uuid.UUID | None = None
    match_score_snapshot: float | None = None


class ListItemBatchCreate(BaseModel):
    items: list[ListItemCreate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_summary(db: Session, lst: models.SavedList) -> dict[str, Any]:
    """Compose the per-list summary used by the lists index and detail."""
    item_count = (
        db.query(func.count(models.SavedListItem.id))
        .filter(models.SavedListItem.list_id == lst.id)
        .scalar()
        or 0
    )
    avg_score = (
        db.query(func.avg(models.SavedListItem.match_score_snapshot))
        .filter(
            models.SavedListItem.list_id == lst.id,
            models.SavedListItem.match_score_snapshot.is_not(None),
        )
        .scalar()
    )
    # Platform mix is computed against the joined influencers; "unknown"
    # bucket covers rows whose primary_platform is null.
    platform_rows = (
        db.query(models.Influencer.primary_platform, func.count(models.SavedListItem.id))
        .join(models.SavedListItem, models.SavedListItem.influencer_id == models.Influencer.id)
        .filter(models.SavedListItem.list_id == lst.id)
        .group_by(models.Influencer.primary_platform)
        .all()
    )
    platform_mix = [
        {
            "platform": (platform or "unknown"),
            "count": int(count),
        }
        for platform, count in platform_rows
    ]
    platform_mix.sort(key=lambda item: -item["count"])

    total_followers = (
        db.query(func.coalesce(func.sum(models.Influencer.follower_count), 0))
        .join(models.SavedListItem, models.SavedListItem.influencer_id == models.Influencer.id)
        .filter(models.SavedListItem.list_id == lst.id)
        .scalar()
    )
    avg_engagement = (
        db.query(func.avg(models.Influencer.engagement_rate))
        .join(models.SavedListItem, models.SavedListItem.influencer_id == models.Influencer.id)
        .filter(
            models.SavedListItem.list_id == lst.id,
            models.Influencer.engagement_rate.is_not(None),
        )
        .scalar()
    )

    return {
        "id": str(lst.id),
        "name": lst.name,
        "status": lst.status,
        "created_at": lst.created_at,
        "updated_at": lst.updated_at,
        "item_count": int(item_count),
        "avg_match_score": round(float(avg_score), 1) if avg_score is not None else None,
        "platform_mix": platform_mix,
        "total_followers": int(total_followers or 0),
        "avg_engagement": round(float(avg_engagement), 2) if avg_engagement is not None else None,
    }


def _list_item(db: Session, item: models.SavedListItem) -> dict[str, Any]:
    inf = (
        db.query(models.Influencer)
        .filter(models.Influencer.id == item.influencer_id)
        .first()
    )
    return {
        "id": str(item.id),
        "influencer_id": str(item.influencer_id),
        "source_campaign_id": (
            str(item.source_campaign_id) if item.source_campaign_id is not None else None
        ),
        "match_score_snapshot": item.match_score_snapshot,
        "added_at": item.added_at,
        "influencer": _influencer_summary(inf) if inf else None,
    }


def _influencer_summary(inf: models.Influencer) -> dict[str, Any]:
    return {
        "id": str(inf.id),
        "canonical_name": inf.canonical_name,
        "primary_platform": inf.primary_platform,
        "primary_handle": inf.primary_handle,
        "primary_category": inf.primary_category,
        "primary_location": inf.primary_location,
        "follower_count": inf.follower_count,
        "engagement_rate": inf.engagement_rate,
        "avg_views": inf.avg_views,
        "platforms": inf.platforms or {},
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[dict[str, Any]])
def list_lists(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return the current user's saved lists with summary aggregates."""
    rows = (
        db.query(models.SavedList)
        .filter(models.SavedList.user_id == current_user.id)
        .order_by(models.SavedList.updated_at.desc())
        .all()
    )
    return [_list_summary(db, lst) for lst in rows]


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_list(
    payload: ListCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new empty list for the current user."""
    lst = models.SavedList(
        user_id=current_user.id,
        name=payload.name,
        status=payload.status,
    )
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return _list_summary(db, lst)


@router.get("/{list_id}", response_model=dict[str, Any])
def get_list(
    list_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return a single list with its items."""
    lst = (
        db.query(models.SavedList)
        .filter(
            models.SavedList.id == list_id,
            models.SavedList.user_id == current_user.id,
        )
        .first()
    )
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")
    items = (
        db.query(models.SavedListItem)
        .filter(models.SavedListItem.list_id == list_id)
        .order_by(models.SavedListItem.added_at.desc())
        .all()
    )
    summary = _list_summary(db, lst)
    summary["items"] = [_list_item(db, item) for item in items]
    return summary


@router.patch("/{list_id}", response_model=dict[str, Any])
def update_list(
    list_id: uuid.UUID,
    payload: ListUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a list's name and/or status."""
    lst = (
        db.query(models.SavedList)
        .filter(
            models.SavedList.id == list_id,
            models.SavedList.user_id == current_user.id,
        )
        .first()
    )
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")
    if payload.name is not None:
        lst.name = payload.name
    if payload.status is not None:
        lst.status = payload.status
    lst.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(lst)
    return _list_summary(db, lst)


@router.delete("/{list_id}")
def delete_list(
    list_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Delete a list (cascade-removes items)."""
    lst = (
        db.query(models.SavedList)
        .filter(
            models.SavedList.id == list_id,
            models.SavedList.user_id == current_user.id,
        )
        .first()
    )
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")
    db.delete(lst)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{list_id}/items",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
def add_list_item(
    list_id: uuid.UUID,
    payload: ListItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a single influencer to a list (idempotent on duplicate)."""
    return _add_items_to_list(
        db,
        current_user=current_user,
        list_id=list_id,
        items=[payload],
    )


@router.post(
    "/{list_id}/items:batch",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
def add_list_items(
    list_id: uuid.UUID,
    payload: ListItemBatchCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add several influencers at once. Used by the Discover "Save selected" flow."""
    return _add_items_to_list(
        db,
        current_user=current_user,
        list_id=list_id,
        items=payload.items,
    )


def _add_items_to_list(
    db: Session,
    *,
    current_user: models.User,
    list_id: uuid.UUID,
    items: list[ListItemCreate],
) -> dict[str, Any]:
    """Shared body for the single + batch item endpoints."""
    lst = (
        db.query(models.SavedList)
        .filter(
            models.SavedList.id == list_id,
            models.SavedList.user_id == current_user.id,
        )
        .first()
    )
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")

    added: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for payload in items:
        influencer = (
            db.query(models.Influencer)
            .filter(models.Influencer.id == payload.influencer_id)
            .first()
        )
        if influencer is None:
            raise HTTPException(
                status_code=404,
                detail=f"Influencer {payload.influencer_id} not found",
            )
        item = models.SavedListItem(
            list_id=lst.id,
            influencer_id=payload.influencer_id,
            source_campaign_id=payload.source_campaign_id,
            match_score_snapshot=payload.match_score_snapshot,
        )
        try:
            db.add(item)
            db.commit()
            db.refresh(item)
            added.append(_list_item(db, item))
        except IntegrityError:
            db.rollback()
            # Duplicate (list, influencer, source_campaign): surface as a
            # structured skipped entry rather than a 409 so the batch
            # endpoint can return partial success.
            skipped.append(
                {
                    "influencer_id": str(payload.influencer_id),
                    "source_campaign_id": (
                        str(payload.source_campaign_id)
                        if payload.source_campaign_id is not None
                        else None
                    ),
                    "reason": "duplicate",
                }
            )

    lst.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(lst)

    return {
        "list": _list_summary(db, lst),
        "added": added,
        "skipped": skipped,
    }


@router.delete(
    "/{list_id}/items/{item_id}",
)
def remove_list_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Remove a single item from a list."""
    # Make sure the list belongs to the current user before touching items.
    lst = (
        db.query(models.SavedList)
        .filter(
            models.SavedList.id == list_id,
            models.SavedList.user_id == current_user.id,
        )
        .first()
    )
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")
    item = (
        db.query(models.SavedListItem)
        .filter(
            models.SavedListItem.id == item_id,
            models.SavedListItem.list_id == list_id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    lst.updated_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
