"""Object-store protocol used for evidence and dataset artefacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True)
class EvidenceRef:
    bucket: str
    key: str
    sha256: str
    size: int


@runtime_checkable
class ObjectStore(Protocol):
    def put_object(
        self,
        tenant_id: UUID,
        bucket: str,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str = "application/octet-stream",
    ) -> EvidenceRef: ...

    def presign_get(
        self,
        tenant_id: UUID,
        bucket: str,
        key: str,
        *,
        expires_seconds: int = 3600,
    ) -> str: ...
