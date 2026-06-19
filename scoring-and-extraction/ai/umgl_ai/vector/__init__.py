"""Vector-store adapters.

The default backend is :mod:`.qdrant`. Other backends (Milvus, pgvector)
can be implemented behind the same :class:`VectorStore` protocol without
touching the rest of the AI runtime.
"""

from .base import VectorHit, VectorStore, VectorUpsertRequest
from .qdrant import QdrantVectorStore, build_default_store

__all__ = [
    "VectorHit",
    "VectorStore",
    "VectorUpsertRequest",
    "QdrantVectorStore",
    "build_default_store",
]
