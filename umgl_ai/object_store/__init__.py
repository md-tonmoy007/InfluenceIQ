"""Object-store adapters. MinIO is the default backend; S3 is wire-compatible."""

from .base import EvidenceRef, ObjectStore
from .minio import MinioObjectStore, build_default_store

__all__ = ["EvidenceRef", "ObjectStore", "MinioObjectStore", "build_default_store"]
