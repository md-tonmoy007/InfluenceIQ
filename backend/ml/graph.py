import math

import networkx as nx

from .contracts import GraphAnalysisRequest, GraphAnalysisResponse, RiskyCluster


class GraphEngine:
    """Weighted community and coordination analysis using NetworkX Louvain."""

    def analyze(self, request: GraphAnalysisRequest) -> GraphAnalysisResponse:
        graph = nx.DiGraph()
        for edge in request.edges:
            current = graph.get_edge_data(edge.source, edge.target, {}).get("weight", 0.0)
            graph.add_edge(
                edge.source,
                edge.target,
                weight=current + edge.weight,
                relation=edge.relation,
            )

        undirected = graph.to_undirected()
        communities = nx.community.louvain_communities(undirected, weight="weight", seed=42)
        clusters: list[RiskyCluster] = []
        for members in communities:
            if len(members) < 3:
                continue
            subgraph = graph.subgraph(members)
            density = nx.density(subgraph)
            reciprocal = nx.reciprocity(subgraph) or 0.0
            concentration = min(1.0, math.log1p(len(members)) / math.log(101))
            score = min(1.0, 0.45 * density + 0.35 * reciprocal + 0.20 * concentration)
            clusters.append(
                RiskyCluster(
                    members=sorted(members),
                    density=density,
                    reciprocity=reciprocal,
                    cluster_risk_score=score,
                )
            )

        clusters.sort(key=lambda item: item.cluster_risk_score, reverse=True)
        graph_risk = max((cluster.cluster_risk_score for cluster in clusters), default=0.0)
        return GraphAnalysisResponse(
            graph_risk_score=graph_risk,
            clusters=clusters,
            metrics={
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "communities": len(communities),
                "density": nx.density(graph),
            },
        )

