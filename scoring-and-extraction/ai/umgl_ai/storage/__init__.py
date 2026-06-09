"""Document-store adapters. The current implementation targets MongoDB."""

from .base import Profile, ProfileStore
from .mongo import MongoProfileStore, build_default_store

__all__ = ["Profile", "ProfileStore", "MongoProfileStore", "build_default_store"]
