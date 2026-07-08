"""Tests for real-comment persistence and legacy-caption cleanup."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")

from backend.pipeline.content.enrichment import persist_post_comments
from backend.pipeline.content.providers.comments.base import RawComment


def _make_post_row():
    post = MagicMock()
    post.id = uuid.uuid4()
    post.platform_post_id = "p1"
    post.fetch_provider = "youtube"
    return post


def _mock_session(existing_rows=None):
    session = MagicMock()
    query = MagicMock()
    filter_ = MagicMock()
    filter_.first.side_effect = (existing_rows or [None]).__iter__()
    filter_.delete = MagicMock()
    query.filter.return_value = filter_
    session.query.return_value = query
    return session, query, filter_


def test_persist_raw_comment_objects():
    session, query, filter_ = _mock_session()
    post = _make_post_row()
    raw = [
        RawComment(
            external_id="c1",
            text="Real audience comment",
            author_key="author1",
            like_count=5,
            published_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            reply_count=2,
        )
    ]
    count = persist_post_comments(session, post, raw, source="youtube_comments")

    assert count == 1
    filter_.delete.assert_called_once()
    assert session.add.call_count == 1
    added = session.add.call_args[0][0]
    assert added.text == "Real audience comment"
    assert added.author_handle_hash is not None
    assert added.like_count == 5
    assert added.published_at is not None
    assert added.raw == {"source": "youtube_comments", "reply_count": 2}


def test_persist_dict_comments():
    session, _, _ = _mock_session()
    post = _make_post_row()
    raw = [
        {
            "external_id": "c2",
            "text": "Dict comment",
            "author_key": "author2",
            "like_count": 3,
            "published_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        }
    ]
    count = persist_post_comments(session, post, raw)

    assert count == 1
    added = session.add.call_args[0][0]
    assert added.text == "Dict comment"
    assert added.author_handle_hash is not None


def test_legacy_caption_rows_deleted_on_refetch():
    session, query, filter_ = _mock_session()
    post = _make_post_row()
    raw = [{"external_id": "c1", "text": "New real comment", "author_key": "a1", "published_at": datetime(2026, 1, 1)}]
    persist_post_comments(session, post, raw)

    # The lazy-cleanup delete is issued for rows with null author/timestamp.
    assert filter_.delete.call_count == 1


def test_skips_empty_text_comments():
    session, _, _ = _mock_session()
    post = _make_post_row()
    raw = [
        {"external_id": "c1", "text": "", "author_key": "a1", "published_at": datetime(2026, 1, 1)},
        {"external_id": "c2", "text": "   ", "author_key": "a2", "published_at": datetime(2026, 1, 1)},
        {"external_id": "c3", "text": "Valid", "author_key": "a3", "published_at": datetime(2026, 1, 1)},
    ]
    count = persist_post_comments(session, post, raw)

    assert count == 1
    added = session.add.call_args[0][0]
    assert added.text == "Valid"


def test_raw_payload_contains_no_author_key():
    session, _, _ = _mock_session()
    post = _make_post_row()
    raw = [RawComment(external_id="c1", text="x", author_key="secret_handle", like_count=None, published_at=None)]
    persist_post_comments(session, post, raw)

    added = session.add.call_args[0][0]
    assert "author" not in (added.raw or {})
    assert "author_key" not in (added.raw or {})
    assert added.author_handle_hash is not None
    assert added.author_handle_hash != "secret_handle"


if __name__ == "__main__":
    test_persist_raw_comment_objects()
    test_persist_dict_comments()
    test_legacy_caption_rows_deleted_on_refetch()
    test_skips_empty_text_comments()
    test_raw_payload_contains_no_author_key()
    print("all persistence tests passed")
