"""Qdrant implementation of the :class:`VectorStore` protocol.

The adapter is HTTP-only so the AI runtime can ship without ``grpcio``.
Tenant isolation is enforced by prefixing every collection name with
``umgl-<tenant-id>``; payload filters are also checked against
``tenant_id`` server-side as a defence in depth.
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from .base import VectorHit, VectorStore, VectorUpsertRequest


def _collection(tenant_id: UUID, name: str) -> str:
    """Tenant-prefix a collection name so Qdrant never mixes tenants."""

    safe = "".join(ch for ch in name if ch.isalnum() or ch in {"_", "-"})
    return f"umgl-{tenant_id}-{safe}"


def _filter(tenant_id: UUID, extra: dict[str, Any] | None) -> dict[str, Any]:
    base = {"must": [{"key": "tenant_id", "match": {"value": str(tenant_id)}}]}
    if extra:
        for key, value in extra.items():
            base["must"].append({"key": key, "match": {"value": value}})
    return base


def build_default_store() -> "QdrantVectorStore":
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    timeout = float(os.getenv("QDRANT_TIMEOUT_SECONDS", "10"))
    return QdrantVectorStore(url=url, api_key=api_key, timeout=timeout)


class QdrantVectorStore:
    def __init__(self, *, url: str, api_key: str | None = None, timeout: float = 10.0) -> None:
        try:
            from qdrant_client import QdrantClient  # type: ignore[import-not-found]
            from qdrant_client.http import models  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - optional extra
            raise RuntimeError(
                "qdrant-client is required for the Qdrant vector backend. "
                "Install it via `pip install qdrant-client>=1.12`."
            ) from error
        self._models = models
        self._client = QdrantClient(url=url, api_key=api_key, timeout=timeout)

    def _ensure(self, collection: str, vector_size: int) -> None:
        if self._client.collection_exists(collection):
            return
        self._client.create_collection(
            collection_name=collection,
            vectors_config=self._models.VectorParams(
                size=vector_size, distance=self._models.Distance.COSINE
            ),
        )

    def upsert(self, request: VectorUpsertRequest) -> None:
        self._ensure(_collection(request.tenant_id, request.collection), len(request.vector))
        payload = {"tenant_id": str(request.tenant_id), **request.payload}
        self._client.upsert(
            collection_name=_collection(request.tenant_id, request.collection),
            points=[self._models.PointStruct(id=request.point_id, vector=request.vector, payload=payload)],
        )

    def search(
        self,
        tenant_id: UUID,
        collection: str,
        vector: list[float],
        *,
        top_k: int = 10,
        score_threshold: float | None = None,
        filter_: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        results = self._client.search(
            collection_name=_collection(tenant_id, collection),
            query_vector=vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=self._models.Filter(**_filter(tenant_id, filter_)),
            with_payload=True,
        )
        return [
            VectorHit(point_id=str(hit.id), score=float(hit.score), payload=dict(hit.payload or {}))
            for hit in results
        ]

    def delete(self, tenant_id: UUID, collection: str, point_id: str) -> None:
        self._client.delete(
            collection_name=_collection(tenant_id, collection),
            points_selector=self._models.PointIdsSelector(points=[point_id]),
        )
