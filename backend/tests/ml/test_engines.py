from uuid import uuid4

from backend.ml.behavioral import BehavioralEngine
from backend.ml.contracts import BehaviorFeatures, GraphAnalysisRequest, GraphEdge
from backend.ml.graph import GraphEngine


def test_automated_behavior_scores_higher_than_normal_behavior() -> None:
    engine = BehavioralEngine()
    normal = BehaviorFeatures(
        tenant_id=uuid4(), subject_id=uuid4(), posts_per_hour=1, median_session_minutes=20,
        account_age_days=1000, engagement_velocity=2, follower_growth_per_day=1,
        duplicate_comment_ratio=0.01, posting_interval_cv=1.2, night_activity_ratio=0.1,
    )
    automated = normal.model_copy(update={
        "posts_per_hour": 30, "account_age_days": 2, "engagement_velocity": 200,
        "follower_growth_per_day": 500, "duplicate_comment_ratio": 0.95,
        "posting_interval_cv": 0.01, "night_activity_ratio": 0.9,
    })
    assert engine.score(automated).behavior_score > engine.score(normal).behavior_score


def test_graph_engine_detects_dense_reciprocal_cluster() -> None:
    nodes = ["a", "b", "c", "d"]
    edges = [GraphEdge(source=a, target=b, relation="follows") for a in nodes for b in nodes if a != b]
    result = GraphEngine().analyze(GraphAnalysisRequest(tenant_id=uuid4(), edges=edges))
    assert result.clusters
    assert result.clusters[0].density == 1.0
    assert result.clusters[0].reciprocity == 1.0

