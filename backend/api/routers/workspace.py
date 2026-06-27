"""Workspace router — dashboard summary, recent activity, and counts.

Single-user-scoped for v1: every endpoint pulls counts / rows for the
authenticated user. A future org/team tenancy layer would scope these
queries by ``org_id`` instead.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from backend.core.auth import get_current_user
from backend.core.database import models
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_PLAN_LIMITS: dict[str, int] = {
    "starter": 5,
    "pro": 25,
    "scale": 100,
}


def _greeting_for_hour(hour: int) -> str:
    """Map a 24h hour to a localized greeting word."""
    if hour < 5:
        return "Working late"
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def _format_date_label(value: datetime) -> str:
    """Render a date for the dashboard sub-headline (e.g. 'Sunday, May 10')."""
    return value.strftime("%A, %B %-d").replace(" 0", " ")


def _derive_brand_name(user: models.User) -> str:
    """Return the user-facing brand label for the dashboard hero."""
    if user.company_name:
        return user.company_name
    # Fall back to the brand profile so onboarded users get a nicer label.
    return user.name or "Workspace"


def _is_terminal(status: str | None) -> bool:
    return status in {"completed", "failed", "partial"}


def _summarize_campaign_row(campaign: models.Campaign) -> dict[str, Any]:
    """Build a compact representation used in the recent_searches feed."""
    snapshot = campaign.brief_snapshot if isinstance(campaign.brief_snapshot, dict) else {}
    query_text = campaign.search_query or snapshot.get("goal") or campaign.campaign_name or campaign.product

    return {
        "campaign_id": str(campaign.id),
        "label": query_text or campaign.product,
        "product": campaign.product,
        "niche": campaign.niche,
        "goal": snapshot.get("goal") or campaign.goals,
        "status": campaign.status,
        "entry_point": campaign.entry_point,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
        "started_at": campaign.started_at,
        "completed_at": campaign.completed_at,
    }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=dict[str, Any])
def workspace_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict[str, Any]:
    """Aggregate everything the dashboard hero, stats, and sidebar need."""
    now = datetime.now(UTC)

    # ----- Hero counts ----------------------------------------------------
    active_count = (
        db.query(func.count(models.Campaign.id))
        .filter(
            models.Campaign.created_by == current_user.id,
            models.Campaign.status.in_(["running", "pending"]),
        )
        .scalar()
        or 0
    )
    completed_count = (
        db.query(func.count(models.Campaign.id))
        .filter(
            models.Campaign.created_by == current_user.id,
            models.Campaign.status == "completed",
        )
        .scalar()
        or 0
    )
    drafts_count = (
        db.query(func.count(models.Campaign.id))
        .filter(
            models.Campaign.created_by == current_user.id,
            models.Campaign.status == "draft",
        )
        .scalar()
        or 0
    )
    failed_count = (
        db.query(func.count(models.Campaign.id))
        .filter(
            models.Campaign.created_by == current_user.id,
            models.Campaign.status == "failed",
        )
        .scalar()
        or 0
    )

    # ----- Saved-list counts ---------------------------------------------
    saved_list_count = (
        db.query(func.count(models.SavedList.id))
        .filter(models.SavedList.user_id == current_user.id)
        .scalar()
        or 0
    )

    # ----- Workspace stats -----------------------------------------------
    # Global influencer catalog count (the "Influencers Indexed" tile).
    indexed_influencers = db.query(func.count(models.Influencer.id)).scalar() or 0

    # "Categories Covered" — distinct niches the user has actually targeted.
    categories_covered = (
        db.query(func.count(distinct(models.Campaign.niche)))
        .filter(models.Campaign.created_by == current_user.id)
        .scalar()
        or 0
    )

    # "Avg Match Score" — average final_score across the user's scores in
    # the last 30 days. Falls back to 0 when no scores exist.
    cutoff = now - timedelta(days=30)
    avg_score_row = (
        db.query(func.avg(models.InfluencerScore.final_score))
        .join(models.Campaign, models.Campaign.id == models.InfluencerScore.campaign_id)
        .filter(
            models.Campaign.created_by == current_user.id,
            models.InfluencerScore.computed_at >= cutoff,
        )
        .scalar()
    )
    avg_match_score = float(avg_score_row) if avg_score_row is not None else 0.0

    # ----- Recent searches -----------------------------------------------
    recent_campaigns = (
        db.query(models.Campaign)
        .filter(models.Campaign.created_by == current_user.id)
        .order_by(models.Campaign.created_at.desc())
        .limit(5)
        .all()
    )
    recent_searches = [_summarize_campaign_row(c) for c in recent_campaigns]

    # ----- Sidebar counts -----------------------------------------------
    sidebar_counts = {
        "briefs": int(active_count + completed_count + drafts_count + failed_count),
        "saved_lists": int(saved_list_count),
        "discover": 0,
    }

    # ----- Upgrade / plan usage -----------------------------------------
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == current_user.id)
        .first()
    )
    plan = subscription.plan if subscription else "starter"
    plan_limit = _PLAN_LIMITS.get(plan, 5)
    monthly_active = int(active_count) + int(drafts_count)
    upgrade_usage = {
        "plan": plan,
        "limit": plan_limit,
        "used": monthly_active,
        "remaining": max(0, plan_limit - monthly_active),
    }

    return {
        "viewer": {
            "user_id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "company_name": _derive_brand_name(current_user),
            "role": current_user.role,
            "timezone": current_user.timezone or "UTC",
        },
        "greeting": {
            "text": _greeting_for_hour(now.hour),
            "date_label": _format_date_label(now),
            "timestamp": now.isoformat(),
        },
        "hero_counts": {
            "active_campaigns": int(active_count),
            "completed_campaigns": int(completed_count),
            "draft_campaigns": int(drafts_count),
            "failed_campaigns": int(failed_count),
            "saved_lists": int(saved_list_count),
        },
        "stats_cards": {
            "indexed_influencers": int(indexed_influencers),
            "categories_covered": int(categories_covered),
            "avg_match_score_30d": round(avg_match_score, 1),
        },
        "recent_searches": recent_searches,
        "sidebar_counts": sidebar_counts,
        "upgrade_usage": upgrade_usage,
    }


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------


@router.get("/activity", response_model=list[dict[str, Any]])
def workspace_activity(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return a merged activity feed (campaigns + lists) for the user."""
    campaigns = (
        db.query(models.Campaign)
        .filter(models.Campaign.created_by == current_user.id)
        .order_by(models.Campaign.created_at.desc())
        .limit(limit)
        .all()
    )
    items: list[dict[str, Any]] = []
    for campaign in campaigns:
        items.append(
            {
                "kind": "campaign",
                "id": str(campaign.id),
                "label": campaign.campaign_name or campaign.product,
                "niche": campaign.niche,
                "status": campaign.status,
                "entry_point": campaign.entry_point,
                "created_at": campaign.created_at,
            }
        )

    lists = (
        db.query(models.SavedList)
        .filter(models.SavedList.user_id == current_user.id)
        .order_by(models.SavedList.created_at.desc())
        .limit(limit)
        .all()
    )
    for lst in lists:
        items.append(
            {
                "kind": "list",
                "id": str(lst.id),
                "label": lst.name,
                "status": lst.status,
                "created_at": lst.created_at,
            }
        )

    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items[:limit]
