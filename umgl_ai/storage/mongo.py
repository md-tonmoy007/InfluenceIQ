"""MongoDB implementation of :class:`ProfileStore`."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from uuid import UUID

from .base import Profile, ProfileStore


def _database(tenant_id: UUID) -> str:
    return f"umgl_{tenant_id.hex}"


def build_default_store() -> "MongoProfileStore":
    return MongoProfileStore(
        uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        database_name=os.getenv("MONGODB_DATABASE", "umgl"),
    )


class MongoProfileStore:
    def __init__(self, *, uri: str, database_name: str = "umgl") -> None:
        try:
            from pymongo import MongoClient, UpdateOne  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - optional extra
            raise RuntimeError(
                "pymongo is required for the MongoDB document store. "
                "Install it via `pip install pymongo>=4.10`."
            ) from error
        self._UpdateOne = UpdateOne
        self._client = MongoClient(uri)
        self._db_name = database_name

    def _collection(self, tenant_id: UUID):
        return self._client[_database(tenant_id)]["profiles"]

    @staticmethod
    def _doc(profile: Profile) -> dict[str, Any]:
        return {
            "tenant_id": str(profile.tenant_id),
            "platform": profile.platform,
            "platform_account_id": profile.platform_account_id,
            "username": profile.username,
            "display_name": profile.display_name,
            "biography": profile.biography,
            "followers": profile.followers,
            "following": profile.following,
            "statuses": profile.statuses,
            "verified": profile.verified,
            "created_at_platform": profile.created_at_platform,
            "last_seen": profile.last_seen or datetime.utcnow(),
            "raw": profile.raw,
        }

    def upsert(self, profile: Profile) -> None:
        self._collection(profile.tenant_id).update_one(
            {"platform": profile.platform, "platform_account_id": profile.platform_account_id},
            {"$set": self._doc(profile)},
            upsert=True,
        )

    def find(
        self, tenant_id: UUID, platform: str, platform_account_id: str
    ) -> Profile | None:
        doc = self._collection(tenant_id).find_one(
            {"platform": platform, "platform_account_id": platform_account_id}
        )
        return self._from_doc(doc) if doc else None

    def list_recent(
        self, tenant_id: UUID, platform: str, *, limit: int = 100
    ) -> list[Profile]:
        cursor = (
            self._collection(tenant_id)
            .find({"platform": platform})
            .sort("last_seen", -1)
            .limit(limit)
        )
        return [self._from_doc(doc) for doc in cursor]

    @staticmethod
    def _from_doc(doc: dict[str, Any]) -> Profile:
        return Profile(
            tenant_id=UUID(doc["tenant_id"]),
            platform=doc["platform"],
            platform_account_id=doc["platform_account_id"],
            username=doc.get("username"),
            display_name=doc.get("display_name"),
            biography=doc.get("biography"),
            followers=int(doc.get("followers", 0)),
            following=int(doc.get("following", 0)),
            statuses=int(doc.get("statuses", 0)),
            verified=bool(doc.get("verified", False)),
            created_at_platform=doc.get("created_at_platform"),
            last_seen=doc.get("last_seen"),
            raw=doc.get("raw", {}),
        )
