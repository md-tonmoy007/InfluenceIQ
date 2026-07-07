"""Tests for the engagement roll-up module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from backend.pipeline.content.engagement_rollup import compute_recent_engagement


@dataclass
class _FakeProfile:
    platform: str = "youtube"
    followers: int | None = 100_000
    posts: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def test_youtube_with_view_stats():
    profile = _FakeProfile(
        posts=[
            {"view_count": 12_000, "like_count": 800, "comment_count": 45, "published_at": "2024-06-01T00:00:00Z"},
            {"view_count": 8_000, "like_count": 500, "comment_count": 30, "published_at": "2024-05-15T00:00:00Z"},
            {"view_count": 10_000, "like_count": 600, "comment_count": 40, "published_at": "2024-05-10T00:00:00Z"},
        ],
    )
    result = compute_recent_engagement(profile)
    assert result["recent_views"] == 10_000
    assert result["recent_likes"] == 633
    assert result["recent_comments"] == 38
    assert result["recent_engagement_rate"] == pytest.approx((633 + 38) / 100_000, rel=0.01)
    assert result["recent_window_days"] == 22


def test_youtube_no_views_falls_back():
    profile = _FakeProfile(
        posts=[
            {"title": "vid 1", "published_at": "2024-06-01T00:00:00Z"},
        ],
        raw={"lifetime_views": 5_000_000},
    )
    result = compute_recent_engagement(profile)
    assert result["recent_views"] is None
    assert result["recent_likes"] is None
    assert result["lifetime_views"] == 5_000_000


def test_engagement_rate_zero_followers():
    profile = _FakeProfile(
        followers=0,
        posts=[
            {"view_count": 1_000, "like_count": 50, "published_at": "2024-01-01T00:00:00Z"},
        ],
    )
    result = compute_recent_engagement(profile)
    assert result["recent_views"] == 1_000
    assert result["recent_engagement_rate"] is None


def test_uses_views_alias_key():
    profile = _FakeProfile(
        posts=[{"views": 5_000, "likes": 200, "published_at": "2024-01-01T00:00:00Z"}],
    )
    result = compute_recent_engagement(profile)
    assert result["recent_views"] == 5_000


def test_empty_posts_returns_nones():
    result = compute_recent_engagement(_FakeProfile())
    assert result["recent_views"] is None
    assert result["recent_likes"] is None
    assert result["recent_comments"] is None
    assert result["recent_window_days"] is None


def test_single_post_window():
    profile = _FakeProfile(
        posts=[{"view_count": 3_000, "published_at": "2024-01-01T00:00:00Z"}],
    )
    result = compute_recent_engagement(profile)
    assert result["recent_window_days"] == 0
