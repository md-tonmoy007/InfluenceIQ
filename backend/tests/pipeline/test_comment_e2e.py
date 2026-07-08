"""End-to-end tests for real comments feeding the fake-risk detectors."""

from __future__ import annotations

import os
import sys
import uuid
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

from backend.pipeline.candidate.builder import build_influencer_candidate
from backend.pipeline.orchestrator.pipeline import run_role4_pipeline


def _make_db_session_with_bot_ring():
    """Return a fake session wired to a bot-ring fixture."""
    _influencer_id = uuid.uuid4()
    _campaign_id = uuid.uuid4()
    _profile_id = uuid.uuid4()
    base_post_time = datetime(2026, 1, 1, 8, 0, 0, tzinfo=UTC)
    base_comment_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    class FakePost:
        def __init__(self, index: int):
            self.id = uuid.uuid4()
            self.platform_profile_id = _profile_id
            self.platform = "youtube"
            self.platform_post_id = f"v{index}"
            self.post_url = f"https://youtube.com/watch?v={index}"
            self.caption = f"Post {index}"
            self.published_at = base_post_time + timedelta(hours=index)

    posts = [FakePost(i) for i in range(5)]

    class FakeComment:
        def __init__(self, post_index: int, author_index: int):
            self.id = uuid.uuid4()
            self.platform_post_id = posts[post_index].id
            self.platform_comment_id = f"c{post_index}_{author_index}"
            self.text = "Great post #trending" if author_index % 2 == 0 else "Love it #trending"
            self.author_handle_hash = f"bot_{author_index}"
            self.published_at = base_comment_time + timedelta(seconds=author_index * 5, milliseconds=post_index * 100)
            self.like_count = None

    comments = [FakeComment(p, a) for p in range(5) for a in range(30)]

    class FakeProfile:
        id = _profile_id
        influencer_id = _influencer_id
        platform = "youtube"
        profile_url = "https://youtube.com/@bottarget"
        bio = ""
        followers = 1000
        avg_engagement = 100
        engagement_rate = 0.05
        verified = False

    class FakeInfluencer:
        id = _influencer_id
        canonical_name = "Bot Target"
        platforms = {"youtube": "https://youtube.com/@bottarget"}
        mentions = []
        credentials = []
        follower_count = 1000
        avg_views = 100
        engagement_rate = 0.05
        primary_location = None
        embedding = None

    class FakeCampaign:
        id = _campaign_id
        search_query = "test"
        niche = ""
        target_audience = ""
        goals = ""
        product = ""
        weights = None
        brief_snapshot = {}
        embedding = None

    class Query:
        def __init__(self, rows):
            self._rows = rows
            self._filters = []

        def filter(self, *args):
            self._filters.extend(args)
            return self

        def join(self, *args):
            return self

        def order_by(self, *args):
            return self

        def limit(self, n):
            return self

        def all(self):
            return self._rows

    class Session:
        def __init__(self):
            self._store = {
                ("Influencer", _influencer_id): FakeInfluencer(),
                ("Campaign", _campaign_id): FakeCampaign(),
            }

        def get(self, model, obj_id):
            return self._store.get((model.__name__, obj_id))

        def query(self, *models):
            if len(models) == 1:
                name = models[0].__name__
                if name == "PlatformProfile":
                    return Query([FakeProfile()])
                if name == "PlatformPost":
                    return Query(posts)
                if name == "PlatformComment":
                    return Query(comments)
                if name == "CrawlSourceInfluencer":
                    return Query([])
                if name == "CrawlSource":
                    return Query([])
            return Query([])

    return Session(), _influencer_id, _campaign_id


def test_candidate_comments_are_dicts_with_author_and_timestamp():
    session, influencer_id, campaign_id = _make_db_session_with_bot_ring()
    candidate = build_influencer_candidate(session, influencer_id, campaign_id)

    assert candidate["comments"]
    assert all(isinstance(c, dict) for c in candidate["comments"])
    assert all(c.get("author_hash") for c in candidate["comments"])
    assert all(c.get("published_at") for c in candidate["comments"])


def test_behavior_features_propagate_to_candidate():
    session, influencer_id, campaign_id = _make_db_session_with_bot_ring()
    candidate = build_influencer_candidate(session, influencer_id, campaign_id)

    assert candidate.get("repeated_commenter_cluster_score", 0) >= 0.5
    assert candidate.get("duplicate_text_cluster_score", 0) >= 0.5
    assert candidate.get("synchronized_activity_score", 0) >= 0.5


def test_pipeline_produces_nonzero_bot_and_coordination_scores():
    session, influencer_id, campaign_id = _make_db_session_with_bot_ring()
    candidate = build_influencer_candidate(session, influencer_id, campaign_id)

    result = run_role4_pipeline(candidate)
    assert result.sub_scores["bot_behavior_risk"] > 0
    assert result.sub_scores["coordinated_engagement_risk"] > 45
    assert result.sub_scores["overall_fake_risk"] > 0
    assert result.signal_scores["bot_behavior_risk_score"] > 0
    assert result.signal_scores["coordinated_engagement_risk_score"] > 45


if __name__ == "__main__":
    test_candidate_comments_are_dicts_with_author_and_timestamp()
    test_behavior_features_propagate_to_candidate()
    test_pipeline_produces_nonzero_bot_and_coordination_scores()
    print("all e2e tests passed")
