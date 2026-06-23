"""Pydantic schemas for the /api/settings and /api/auth/me endpoints.

Kept in its own module so the auth and onboarding routers stay small.
The shape of these models mirrors the ORM classes in
:mod:`backend.core.database.models` (with ``from_attributes=True`` on
the read-only responses) and the request payloads that the
``/settings`` page sends up.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# /api/auth/me
# ---------------------------------------------------------------------------


class UpdateProfileRequest(BaseModel):
    """Partial update of the current user's profile.

    All fields optional so a single endpoint can be used for "save name
    only" as well as "save everything". ``email`` and ``company_name``
    are intentionally absent — the settings page shows email as
    read-only and the company name comes from the signup flow.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=64)


class ChangePasswordRequest(BaseModel):
    """Password change payload — current password is required to confirm ownership."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


# ---------------------------------------------------------------------------
# /api/settings/notifications
# ---------------------------------------------------------------------------


class NotificationPreferencesRequest(BaseModel):
    """All four notification toggles; the UI sends the full object on save."""

    shortlist_ready: bool
    creator_replied: bool
    weekly_digest: bool
    product_updates: bool


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    shortlist_ready: bool
    creator_replied: bool
    weekly_digest: bool
    product_updates: bool
    updated_at: datetime


# ---------------------------------------------------------------------------
# /api/settings/integrations
# ---------------------------------------------------------------------------


class IntegrationStatusResponse(BaseModel):
    """One provider's connect state for the current user."""

    provider: str
    connected: bool
    connected_at: datetime | None = None


# ---------------------------------------------------------------------------
# /api/settings/api-keys
# ---------------------------------------------------------------------------


class ApiKeyResponse(BaseModel):
    """List-row shape. The full key is never returned here — only the prefix."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key_prefix: str
    created_at: datetime
    revoked_at: datetime | None = None


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned exactly once by ``POST /api/settings/api-keys`` with the full key.

    The frontend must surface this to the user in a copy-able banner
    and never store the ``key`` field beyond the lifetime of the page.
    """

    key: str


# ---------------------------------------------------------------------------
# /api/settings/subscription
# ---------------------------------------------------------------------------


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: str
    updated_at: datetime


class SubscriptionUpdateRequest(BaseModel):
    """Stub: the UI sends a new plan string and we just flip the field."""

    plan: str = Field(..., min_length=1, max_length=64)
