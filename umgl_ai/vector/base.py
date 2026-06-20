"""Protocols and DTOs for pluggable vector stores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True)
class VectorUpsertRequest:
    tenant_id: UUID
    collection: str
    point_id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorHit:
    point_id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    """The contract every vector-store backend must satisfy."""

    def upsert(self, request: VectorUpsertRequest) -> None: ...
    def search(
        self,
        tenant_id: UUID,
        collection: str,
        vector: list[float],
        *,
        top_k: int = 10,
        score_threshold: float | None = None,
        filter_: dict[str, Any] | None = None,
    ) -> list[VectorHit]: ...
    def delete(self, tenant_id: UUID, collection: str, point_id: str) -> None: ...
