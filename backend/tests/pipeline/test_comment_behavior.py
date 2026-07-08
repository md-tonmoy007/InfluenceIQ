"""Tests for the audience-comment behavioral feature extractor."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.pipeline.analysis.bot_behavior import score_bot_behavior
from backend.pipeline.analysis.comment_behavior import extract_behavior_features
from backend.pipeline.analysis.coordinated_engagement import score_coordinated_engagement


def _make_comment(post_id: str, author: str, text: str, offset_minutes: int) -> dict:
    return {
        "post_external_id": post_id,
        "author_hash": author,
        "text": text,
        "published_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC) + timedelta(minutes=offset_minutes),
    }


def test_organic_scenario_features_low():
    import random
    random.seed(42)
    # Irregular posting window so interval uniformity stays low.
    post_times = [
        datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 14, 30, 0, tzinfo=UTC),
        datetime(2026, 1, 5, 9, 15, 0, tzinfo=UTC),
        datetime(2026, 1, 11, 20, 45, 0, tzinfo=UTC),
        datetime(2026, 1, 25, 7, 10, 0, tzinfo=UTC),
        datetime(2026, 2, 15, 22, 0, 0, tzinfo=UTC),
    ]
    posts = [{"external_id": f"p{i}", "published_at": t} for i, t in enumerate(post_times)]
    comments = []
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    for i in range(200):
        # Random-ish offsets so per-post comment intervals are irregular.
        offset_seconds = random.randint(0, 48 * 3600)
        comments.append({
            "post_external_id": f"p{i % 6}",
            "author_hash": f"author_{i}",
            "text": f"unique comment {i}",
            "published_at": base + timedelta(seconds=offset_seconds),
        })

    features = extract_behavior_features(posts, comments)
    assert features
    for key, value in features.items():
        assert value < 0.2, f"{key} = {value} should be < 0.2 for organic fixture"


def test_bot_ring_produces_high_coordination():
    posts = [{"external_id": f"p{i}", "published_at": datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC) + timedelta(hours=i)} for i in range(6)]
    comments = []
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    # Keep every bot's comments within a 3-minute window so all pairs co-comment.
    for author_index in range(30):
        for post_index in range(5):
            comments.append({
                "post_external_id": f"p{post_index}",
                "author_hash": f"bot_{author_index}",
                "text": "Great post #trending" if author_index % 2 == 0 else "Love it #trending",
                "published_at": base + timedelta(seconds=author_index * 5, milliseconds=post_index * 100),
            })

    features = extract_behavior_features(posts, comments)
    assert features["repeated_commenter_cluster_score"] >= 0.5
    assert features["duplicate_text_cluster_score"] >= 0.5
    assert features["synchronized_activity_score"] >= 0.5

    score_bot_behavior(features)
    coord_result = score_coordinated_engagement(features)
    assert coord_result["coordinated_engagement_risk_score"] > 45


def test_insufficient_comments_returns_empty():
    posts = [{"external_id": "p1", "published_at": datetime(2026, 1, 1)}]
    comments = [_make_comment("p1", "a1", "hi", i) for i in range(12)]
    assert extract_behavior_features(posts, comments) == {}


if __name__ == "__main__":
    test_organic_scenario_features_low()
    test_bot_ring_produces_high_coordination()
    test_insufficient_comments_returns_empty()
    print("all behavior tests passed")
