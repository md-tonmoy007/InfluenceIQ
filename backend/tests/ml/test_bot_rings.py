from uuid import uuid4

from backend.ml.bot_rings import detect_rings
from backend.ml.contracts import GraphAnalysisRequest, GraphEdge


def _complete(nodes: list[str]) -> list[GraphEdge]:
    return [GraphEdge(source=a, target=b, relation="follows") for a in nodes for b in nodes if a != b]


def test_detect_rings_flags_dense_reciprocal_cluster() -> None:
    edges = _complete(["a", "b", "c", "d"])
    result = detect_rings(GraphAnalysisRequest(tenant_id=uuid4(), edges=edges))
    assert result.clusters, "expected at least one cluster"
    assert result.clusters[0].cluster_risk_score > 0.6


def test_detect_rings_ignores_sparse_graph() -> None:
    edges = [GraphEdge(source="a", target="b", relation="follows")]
    result = detect_rings(GraphAnalysisRequest(tenant_id=uuid4(), edges=edges))
    assert result.clusters == []
    assert result.graph_risk_score == 0.0


def test_detect_rings_merges_overlapping_communities() -> None:
    # Two cliques sharing a single bridge.
    edges = (
        _complete(["a", "b", "c"])
        + _complete(["c", "d", "e"])
        + [GraphEdge(source="a", target="d", relation="follows")]
    )
    result = detect_rings(GraphAnalysisRequest(tenant_id=uuid4(), edges=edges))
    assert any(len(c.members) >= 5 for c in result.clusters)
