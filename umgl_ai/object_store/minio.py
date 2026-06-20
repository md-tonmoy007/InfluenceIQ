"""MinIO (S3-compatible) implementation of :class:`ObjectStore`."""

from __future__ import annotations

import hashlib
import os
from typing import BinaryIO
from uuid import UUID

from .base import EvidenceRef, ObjectStore


def _tenant_bucket(tenant_id: UUID, bucket: str) -> str:
    return f"umgl-{tenant_id}-{bucket}".lower()


def build_default_store() -> "MinioObjectStore":
    return MinioObjectStore(
        endpoint=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "umgl"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "change-me"),
        secure=os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"},
    )


class MinioObjectStore:
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        region: str | None = None,
    ) -> None:
        try:
            from minio import Minio  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - optional extra
            raise RuntimeError(
                "minio is required for the MinIO object-store backend. "
                "Install it via `pip install minio>=7.2`."
            ) from error
        self._client = Minio(
            endpoint.replace("http://", "").replace("https://", ""),
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

    def _ensure(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def put_object(
        self,
        tenant_id: UUID,
        bucket: str,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str = "application/octet-stream",
    ) -> EvidenceRef:
        bucket_name = _tenant_bucket(tenant_id, bucket)
        self._ensure(bucket_name)
        data = stream.read()
        digest = hashlib.sha256(data).hexdigest()
        from io import BytesIO

        self._client.put_object(
            bucket_name,
            key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return EvidenceRef(bucket=bucket_name, key=key, sha256=digest, size=len(data))

    def presign_get(
        self,
        tenant_id: UUID,
        bucket: str,
        key: str,
        *,
        expires_seconds: int = 3600,
    ) -> str:
        from datetime import timedelta

        return self._client.presigned_get_object(
            _tenant_bucket(tenant_id, bucket), key, expires=timedelta(seconds=expires_seconds)
        )
