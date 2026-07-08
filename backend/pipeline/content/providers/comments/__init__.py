"""Per-platform audience-comment fetchers."""

from backend.pipeline.content.providers.comments.base import (
    RawComment,
    fetch_post_comments,
)

__all__ = ["RawComment", "fetch_post_comments"]
