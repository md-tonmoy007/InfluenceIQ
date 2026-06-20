"""Additional DTOs shared by the AI runtime and the service kit.

Lives in its own module to avoid forcing the kit to import
pydantic/FastAPI types; the kit only reads the JSON shapes.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FinalRiskRequest(BaseModel):
    tenant_id: UUID
    subject_id: UUID
    signals: dict[str, tuple[float, float]] = Field(
        default_factory=dict,
        description="Mapping of signal name to (score in [0,1], weight > 0). "
        "Use a negative score to mark a signal as missing.",
    )
    calibrated: bool = True


class FinalRiskResponse(BaseModel):
    subject_id: UUID
    risk_score: float = Field(ge=0, le=1)
    category: str
    effective_weights: dict[str, float]
    missing_signals: list[str]
    model_version: str


class VectorUpsertBody(BaseModel):
    tenant_id: UUID
    collection: str = Field(min_length=1, max_length=64)
    point_id: str = Field(min_length=1, max_length=128)
    vector: list[float] = Field(min_length=1, max_length=8192)
    payload: dict[str, Any] = Field(default_factory=dict)


class VectorSearchBody(BaseModel):
    tenant_id: UUID
    collection: str = Field(min_length=1, max_length=64)
    vector: list[float] = Field(min_length=1, max_length=8192)
    top_k: int = Field(default=10, ge=1, le=1_000)
    score_threshold: float | None = Field(default=None, ge=0, le=1)
    filter_: dict[str, Any] | None = None


class VectorSearchHit(BaseModel):
    point_id: str
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


class VectorSearchResponse(BaseModel):
    hits: list[VectorSearchHit]


class EvidenceUploadResponse(BaseModel):
    bucket: str
    key: str
    sha256: str
    size: int
    presigned_url: str | None = None
