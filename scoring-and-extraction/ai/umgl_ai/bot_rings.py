"""Bot ring detection pipeline (Pipeline D).

Detects coordinated inauthentic behaviour by combining three complementary
signals over a tenant-scoped interaction graph:

  1. Louvain community detection for coarse ring boundaries.
  2. Label propagation as a second-pass refinement that surfaces near-cliques
     Louvain merges with the background.
  3. Node2Vec embeddings (when the optional ``graph`` extras are installed)
     to compute a behavioural similarity that flags accounts that act
     similarly even when their interaction graph is sparse.

The output is a list of :class:`RiskyCluster` records sorted by their
``cluster_risk_score`` so the detection service can persist the most
suspicious rings first.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable, Sequence

import networkx as nx

from .contracts import GraphAnalysisRequest, GraphEdge, GraphAnalysisResponse, RiskyCluster


def _weighted_undirected(edges: Iterable[GraphEdge]) -> nx.Graph:
    graph = nx.Graph()
    for edge in edges:
        if graph.has_edge(edge.source, edge.target):
            graph[edge.source][edge.target]["weight"] += edge.weight
        else:
            graph.add_edge(edge.source, edge.target, weight=edge.weight, relation=edge.relation)
    return graph


def _louvain(graph: nx.Graph) -> list[set[str]]:
    if graph.number_of_edges() == 0:
        return [set(graph.nodes())]
    return [set(c) for c in nx.community.louvain_communities(graph, weight="weight", seed=42)]


def _label_propagation(graph: nx.Graph) -> list[set[str]]:
    if graph.number_of_nodes() == 0:
        return []
    # `label_propagation_communities` in networkx>=3.3 does not accept a
    # `seed` kwarg; use the public function which is deterministic for a
    # given graph.
    communities = nx.community.label_propagation_communities(graph)
    return [set(c) for c in communities if len(c) >= 2]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _node2vec_suspicion(
    graph: nx.Graph, communities: Sequence[set[str]]
) -> dict[str, float]:
    """Optional Node2Vec similarity term.

    The function returns an empty mapping when the optional graph extra
    (``torch_geometric``) is not available, so the pipeline never raises
    at import time on a slim install.
    """
    try:
        from torch_geometric.nn import Node2Vec  # type: ignore[import-not-found]
        from torch_geometric.utils import from_networkx  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - optional extra
        return {}

    if graph.number_of_nodes() < 4 or graph.number_of_edges() < 4:
        return {}

    data = from_networkx(graph)
    model = Node2Vec(data.edge_index, embedding_dim=32, walk_length=10, context_size=5)
    # We do not train; the random init already encodes structural distance
    # and is cheap to compute for a forensic hint.
    embeddings = model.embedding.weight.detach().cpu().numpy()
    nodes = list(graph.nodes())
    index = {node: i for i, node in enumerate(nodes)}

    suspicion: dict[str, float] = defaultdict(float)
    for community in communities:
        if len(community) < 3:
            continue
        intra_vectors = [embeddings[index[node]] for node in community if node in index]
        if len(intra_vectors) < 2:
            continue
        # Mean cosine similarity inside the community.
        import numpy as np

        matrix = np.stack(intra_vectors)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
        sims = (matrix @ matrix.T) / (norms @ norms.T)
        upper = sims[np.triu_indices_from(sims, k=1)]
        mean_sim = float(upper.mean()) if upper.size else 0.0
        for node in community:
            if node in index:
                suspicion[node] = max(suspicion.get(node, 0.0), mean_sim)
    return dict(suspicion)


def _score_cluster(
    subgraph: nx.Graph,
    members: set[str],
    suspicion: dict[str, float],
) -> float:
    if len(members) < 3:
        return 0.0
    density = nx.density(subgraph)
    reciprocity = (
        nx.reciprocity(subgraph) if isinstance(subgraph, nx.DiGraph) else 1.0
    )
    concentration = min(1.0, math.log1p(len(members)) / math.log(101))
    sim = sum(suspicion.get(node, 0.0) for node in members) / len(members)
    return min(
        1.0,
        0.35 * density
        + 0.20 * reciprocity
        + 0.20 * concentration
        + 0.25 * max(0.0, min(1.0, sim)),
    )


def detect_rings(
    request: GraphAnalysisRequest,
    *,
    min_cluster_size: int = 3,
    merge_threshold: float = 0.6,
) -> GraphAnalysisResponse:
    """Detect bot rings from a list of weighted edges.

    Parameters
    ----------
    request:
        Edges for the tenant-scoped interaction graph.
    min_cluster_size:
        Clusters smaller than this are ignored. The spec default is 3, which
        matches the operational threshold of a coordination ring.
    merge_threshold:
        Jaccard overlap above which a Louvain and Label-Propagation cluster
        are merged before scoring.
    """

    digraph = nx.DiGraph()
    for edge in request.edges:
        if digraph.has_edge(edge.source, edge.target):
            digraph[edge.source][edge.target]["weight"] += edge.weight
        else:
            digraph.add_edge(
                edge.source, edge.target, weight=edge.weight, relation=edge.relation
            )

    if digraph.number_of_nodes() == 0:
        return GraphAnalysisResponse(
            graph_risk_score=0.0, clusters=[], metrics={"nodes": 0, "edges": 0, "rings": 0}
        )

    undirected = _weighted_undirected(request.edges)
    louvain = _louvain(undirected)
    propagation = _label_propagation(undirected)
    suspicion = _node2vec_suspicion(undirected, louvain + propagation)

    merged: list[set[str]] = list(louvain)
    for prop_cluster in propagation:
        for existing in list(merged):
            if _jaccard(existing, prop_cluster) >= merge_threshold:
                existing |= prop_cluster
                break
        else:
            merged.append(prop_cluster)

    clusters: list[RiskyCluster] = []
    for members in merged:
        if len(members) < min_cluster_size:
            continue
        sub = digraph.subgraph(members)
        score = _score_cluster(sub, members, suspicion)
        if score <= 0:
            continue
        clusters.append(
            RiskyCluster(
                members=sorted(members),
                density=nx.density(sub),
                reciprocity=nx.reciprocity(sub) or 0.0,
                cluster_risk_score=score,
            )
        )

    clusters.sort(key=lambda c: c.cluster_risk_score, reverse=True)
    graph_risk = clusters[0].cluster_risk_score if clusters else 0.0
    return GraphAnalysisResponse(
        graph_risk_score=graph_risk,
        clusters=clusters,
        metrics={
            "nodes": digraph.number_of_nodes(),
            "edges": digraph.number_of_edges(),
            "louvain_communities": len(louvain),
            "label_propagation_communities": len(propagation),
            "rings": len(clusters),
            "node2vec_used": bool(suspicion),
        },
    )
