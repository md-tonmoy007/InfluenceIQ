"""Settings router — notifications, integrations, API keys, subscription.

All endpoints are scoped to the current user. Each resource follows
the same upsert-by-user pattern as :mod:`backend.api.routers.onboarding`
so a save from the settings page creates the row on first call and
updates it on subsequent calls.

This module intentionally has no Stripe or real OAuth wiring — those
endpoints flip a boolean in the DB and are documented as "stub" in
the API description.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.api.schemas.settings import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    IntegrationStatusResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from backend.core.auth import get_current_user, hash_password
from backend.core.database.models import (
    ApiKey,
    IntegrationConnection,
    NotificationPreference,
    Subscription,
    User,
)
from backend.core.database.session import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def _get_or_create_notification_prefs(
    db: Session, user_id: uuid.UUID
) -> NotificationPreference:
    """Return the user's notification prefs, creating the row if missing.

    The defaults baked into the model match the legacy
    ``SettingsToggles`` component (shortlist + creator + product on,
    weekly digest off) so first-time visitors see the familiar state
    even before the first save.
    """
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )
    if prefs is None:
        prefs = NotificationPreference(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/notifications", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationPreference:
    """Return the current user's notification preferences (creating the row on demand)."""
    return _get_or_create_notification_prefs(db, current_user.id)


@router.put("/notifications", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    payload: NotificationPreferencesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationPreference:
    """Upsert the current user's notification preferences."""
    prefs = _get_or_create_notification_prefs(db, current_user.id)
    prefs.shortlist_ready = payload.shortlist_ready
    prefs.creator_replied = payload.creator_replied
    prefs.weekly_digest = payload.weekly_digest
    prefs.product_updates = payload.product_updates
    prefs.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(prefs)
    return prefs


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------

# Providers the UI knows about. Keeping it as a server-side constant
# means a typo on the client surfaces as 404 instead of an orphan
# row in the DB.
SUPPORTED_PROVIDERS = ("slack", "hubspot")


def _get_or_create_integration(
    db: Session, user_id: uuid.UUID, provider: str
) -> IntegrationConnection:
    """Return the row for ``(user_id, provider)``, creating it on demand."""
    row = (
        db.query(IntegrationConnection)
        .filter(
            IntegrationConnection.user_id == user_id,
            IntegrationConnection.provider == provider,
        )
        .first()
    )
    if row is None:
        row = IntegrationConnection(user_id=user_id, provider=provider, connected=False)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/integrations", response_model=list[IntegrationStatusResponse])
def list_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IntegrationStatusResponse]:
    """Return the connect state for every supported provider."""
    rows: list[IntegrationStatusResponse] = []
    for provider in SUPPORTED_PROVIDERS:
        row = _get_or_create_integration(db, current_user.id, provider)
        rows.append(
            IntegrationStatusResponse(
                provider=row.provider,
                connected=row.connected,
                connected_at=row.connected_at,
            )
        )
    return rows


@router.post(
    "/integrations/{provider}/connect",
    response_model=IntegrationStatusResponse,
)
def connect_integration(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationStatusResponse:
    """Mark ``provider`` as connected for the current user (stub — no real OAuth)."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider}",
        )
    row = _get_or_create_integration(db, current_user.id, provider)
    row.connected = True
    row.connected_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return IntegrationStatusResponse(
        provider=row.provider,
        connected=row.connected,
        connected_at=row.connected_at,
    )


@router.post(
    "/integrations/{provider}/disconnect",
    response_model=IntegrationStatusResponse,
)
def disconnect_integration(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationStatusResponse:
    """Mark ``provider`` as disconnected for the current user."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider}",
        )
    row = _get_or_create_integration(db, current_user.id, provider)
    row.connected = False
    row.connected_at = None
    db.commit()
    db.refresh(row)
    return IntegrationStatusResponse(
        provider=row.provider,
        connected=row.connected,
        connected_at=row.connected_at,
    )


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApiKey]:
    """Return all non-revoked API keys belonging to the current user."""
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
        .all()
    )


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyCreatedResponse:
    """Generate a new API key for the current user.

    The full key is shown in the response exactly once — the DB only
    stores the prefix and the bcrypt hash. We reuse
    :func:`backend.core.auth.hash_password` (bcrypt) for the hash so
    a single context handles every secret on the system.
    """
    raw_key = secrets.token_urlsafe(32)
    key_prefix = raw_key[:8]
    key_hash = hash_password(raw_key)

    row = ApiKey(
        user_id=current_user.id,
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ApiKeyCreatedResponse(
        id=row.id,
        key_prefix=row.key_prefix,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
        key=raw_key,
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Revoke a previously-issued API key. 404 if it's not the caller's or already revoked."""
    row = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        .first()
    )
    if row is None or row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    row.revoked_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Subscription (stub)
# ---------------------------------------------------------------------------


def _get_or_create_subscription(db: Session, user_id: uuid.UUID) -> Subscription:
    """Return the user's subscription, creating the row if missing."""
    sub = (
        db.query(Subscription).filter(Subscription.user_id == user_id).first()
    )
    if sub is None:
        sub = Subscription(user_id=user_id, plan="starter")
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subscription:
    """Return the current user's plan (``"starter"`` if no row yet)."""
    return _get_or_create_subscription(db, current_user.id)


@router.post("/subscription", response_model=SubscriptionResponse)
def update_subscription(
    payload: SubscriptionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subscription:
    """Stub: update the current user's ``plan`` field directly.

    No payment processing, no Stripe — the settings UI calls this
    from the "Upgrade to Pro" / "Compare plans" buttons. The free-text
    ``plan`` field accepts any non-empty string but the UI only sends
    ``"starter"``, ``"pro"``, or ``"scale"``.
    """
    sub = _get_or_create_subscription(db, current_user.id)
    sub.plan = payload.plan
    sub.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(sub)
    return sub
