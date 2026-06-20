"""Document-store protocol for raw social-actor profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@dataclass
class Profile:
    tenant_id: UUID
    platform: str
    platform_account_id: str
    username: str | None = None
    display_name: str | None = None
    biography: str | None = None
    followers: int = 0
    following: int = 0
    statuses: int = 0
    verified: bool = False
    created_at_platform: datetime | None = None
    last_seen: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ProfileStore(Protocol):
    def upsert(self, profile: Profile) -> None: ...
    def find(
        self, tenant_id: UUID, platform: str, platform_account_id: str
    ) -> Profile | None: ...
    def list_recent(
        self, tenant_id: UUID, platform: str, *, limit: int = 100
    ) -> list[Profile]: ...
