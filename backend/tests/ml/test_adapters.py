"""Adapter protocol tests.

These tests never reach an external service. They verify the contract
implementations satisfy the runtime-checkable protocol and that the pure
helpers behave as documented.
"""

from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pytest

from backend.ml.stores.document import MongoProfileStore, Profile, ProfileStore
from backend.ml.stores.object import EvidenceRef, MinioObjectStore, ObjectStore
from backend.ml.stores.vector import QdrantVectorStore, VectorHit, VectorStore


def test_qdrant_store_satisfies_protocol() -> None:
    store = QdrantVectorStore(url="http://localhost:6333")
    assert isinstance(store, VectorStore)


def test_minio_store_satisfies_protocol() -> None:
    pytest.importorskip("minio")
    store = MinioObjectStore(endpoint="localhost:9000", access_key="x", secret_key="y")
    assert isinstance(store, ObjectStore)
    assert isinstance(EvidenceRef("b", "k", "h", 1), EvidenceRef)


def test_mongo_store_satisfies_protocol() -> None:
    pytest.importorskip("pymongo")
    store = MongoProfileStore(uri="mongodb://localhost:27017")
    assert isinstance(store, ProfileStore)


def test_vector_hit_roundtrip() -> None:
    hit = VectorHit(point_id="p1", score=0.9, payload={"kind": "evidence"})
    assert hit.score == 0.9
    assert hit.payload["kind"] == "evidence"


def test_profile_dataclass_is_typed() -> None:
    profile = Profile(
        tenant_id=uuid4(),
        platform="x",
        platform_account_id="42",
        username="alice",
        followers=10,
        following=2,
        last_seen=datetime.utcnow(),
    )
    assert profile.platform == "x"
    assert profile.followers == 10


def test_minio_put_object_hashes_payload(monkeypatch) -> None:
    pytest.importorskip("minio")
    class _FakeClient:
        def bucket_exists(self, _bucket: str) -> bool:
            return True

        def put_object(self, _bucket: str, _key: str, _data, length: int, content_type: str) -> None:
            self.length = length
            self.content_type = content_type

    fake = _FakeClient()
    store = MinioObjectStore(endpoint="localhost:9000", access_key="x", secret_key="y")
    store._client = fake  # type: ignore[attr-defined]
    ref = store.put_object(uuid4(), "evidence", "k1", BytesIO(b"hello"))
    assert ref.size == 5
    assert ref.sha256
