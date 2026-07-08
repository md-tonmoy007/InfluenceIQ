"""Comment-fetch contract and platform dispatch.

Real audience comments are fetched per-post by dedicated providers and
returned as :class:`RawComment` objects. The enrichment layer hashes the
author handle before persistence so no PII is stored.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from backend.pipeline.content.cache import (
    provider_is_available,
    record_provider_failure,
)

log = logging.getLogger(__name__)


@dataclass
class RawComment:
    """A single fetched audience comment.

    ``author_key`` is the raw handle/channel-id returned by the upstream
    API. It is hashed before persistence and never stored as-is.
    """

    external_id: str          # platform comment id
    text: str
    author_key: str           # raw handle/channel-id — hashed before persist
    like_count: int | None
    published_at: datetime | None
    reply_count: int | None = None


PROVIDER_NAMES: dict[str, str] = {
    "youtube": "youtube_comments",
    "instagram": "apify_instagram_comments",
    "tiktok": "apify_tiktok_comments",
}


def fetch_post_comments(
    platform: str,
    post_url: str,
    post_external_id: str,
    limit: int,
) -> list[RawComment]:
    """Dispatch to the per-platform comment fetcher.

    Failures degrade to ``[]`` so a comment-provider outage can never fail
    an enrich->score or deep-analysis chain.
    """
    provider = PROVIDER_NAMES.get(platform)
    if provider is None:
        log.debug("fetch_post_comments unsupported platform=%s", platform)
        return []

    if not provider_is_available(provider):
        log.debug("fetch_post_comments provider=%s circuit-open", provider)
        return []

    try:
        if platform == "youtube":
            from backend.pipeline.content.providers.comments.youtube import (
                fetch_youtube_post_comments,
            )

            return fetch_youtube_post_comments(post_external_id, limit)
        if platform == "instagram":
            from backend.pipeline.content.providers.comments.instagram import (
                fetch_instagram_post_comments,
            )

            return fetch_instagram_post_comments(post_url, limit)
        if platform == "tiktok":
            from backend.pipeline.content.providers.comments.tiktok import (
                fetch_tiktok_post_comments,
            )

            return fetch_tiktok_post_comments(post_url, limit)
    except Exception as exc:
        log.warning("fetch_post_comments failed platform=%s post=%s: %s", platform, post_external_id or post_url, exc)
        record_provider_failure(provider)
        return []

    return []
