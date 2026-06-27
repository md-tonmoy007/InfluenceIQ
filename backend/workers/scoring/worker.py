from __future__ import annotations

from backend.core.celery.app import celery_app

from backend.pipeline.tasks.extract import (  # noqa: F401
    extract_influencers,
    resolve_identity_cluster,
)
from backend.pipeline.tasks.score import score_influencer  # noqa: F401
