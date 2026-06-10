from __future__ import annotations

from datetime import UTC, datetime

from app.config import settings


def score_metadata(data_source_count: int) -> dict[str, str | int]:
    return {
        "score_version": settings.SCORE_VERSION,
        "computed_at": datetime.now(UTC).isoformat(),
        "data_source_count": data_source_count,
    }
