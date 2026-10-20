from gemma_research.data.types import CodeGraph, Edge, Node
from gemma_research.evidence.perturb import (
    high_centrality_edges,
    missing_edges,
    node_omission,
    stale_rewire,
    stale_symbol_refs,
)


def _toy_graph() -> CodeGraph:
    nodes = tuple(
        Node(node_id=f"n{i}", repo="toy", kind="function", text=f"function n{i} does thing {i}")
        for i in range(10)
    )
    edges = tuple(
        Edge(src=f"n{i}", dst=f"n{(i + 1) % 10}", edge_type="calls") for i in range(10)
    ) + tuple(Edge(src=f"n{i}", dst=f"n{(i + 3) % 10}", edge_type="imports") for i in range(10))
    return CodeGraph(repo="toy", commit="abc123", nodes=nodes, edges=edges)


def test_missing_edges_removes_expected_fraction_per_type():
    graph = _toy_graph()
    new_graph, manifest = missing_edges(graph, severity=0.4, seed=1)
    assert len(manifest.removed_edges) == 8  # 4/10 "calls" + 4/10 "imports"
    assert len(new_graph.edges) == len(graph.edges) - len(manifest.removed_edges)
    assert new_graph.nodes == graph.nodes  # nodes/answer labels untouched


def test_missing_edges_is_deterministic():
    graph = _toy_graph()
    g1, m1 = missing_edges(graph, severity=0.3, seed=42)
    g2, m2 = missing_edges(graph, severity=0.3, seed=42)
    assert g1.edges == g2.edges
    assert m1.removed_edges == m2.removed_edges


def test_missing_edges_different_seeds_differ():
    graph = _toy_graph()
    g1, _ = missing_edges(graph, severity=0.3, seed=1)
    g2, _ = missing_edges(graph, severity=0.3, seed=2)
    assert g1.edges != g2.edges


def test_node_omission_hides_nodes_and_incident_edges():
    graph = _toy_graph()
    new_graph, manifest = node_omission(graph, severity=0.3, seed=7)
    assert len(manifest.hidden_node_ids) == 3
    assert len(new_graph.nodes) == 7
    for e in new_graph.edges:
        assert e.src not in manifest.hidden_node_ids
        assert e.dst not in manifest.hidden_node_ids


def test_stale_rewire_preserves_edge_count_and_changes_targets():
    graph = _toy_graph()
    new_graph, manifest = stale_rewire(graph, severity=0.5, seed=3)
    assert len(new_graph.edges) == len(graph.edges)
    assert len(manifest.rewired_edges) > 0
    for old_edge, new_edge in manifest.rewired_edges:
        assert old_edge.src == new_edge.src
        assert old_edge.dst != new_edge.dst


def test_severity_zero_is_a_no_op_control():
    graph = _toy_graph()
    new_graph, manifest = missing_edges(graph, severity=0.0, seed=1)
    assert set(new_graph.edges) == set(graph.edges)  # same edge set; order is not guaranteed
    assert manifest.removed_edges == ()


def test_invalid_severity_rejected():
    graph = _toy_graph()
    try:
        missing_edges(graph, severity=1.5, seed=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for out-of-range severity")


def test_high_centrality_edges_removes_highest_degree_first():
    # n0 gets extra incident edges so it has the highest degree in the graph.
    nodes = tuple(Node(f"n{i}", "toy", "function", f"fn {i}") for i in range(6))
    edges = (
        Edge("n0", "n1", "calls"),
        Edge("n0", "n2", "calls"),
        Edge("n0", "n3", "calls"),
        Edge("n4", "n5", "calls"),
    )
    graph = CodeGraph(repo="toy", commit="abc", nodes=nodes, edges=edges)
    new_graph, manifest = high_centrality_edges(graph, severity=0.25, seed=1)
    assert len(manifest.removed_edges) == 1
    assert manifest.removed_edges[0].src == "n0"  # highest-degree endpoint removed first
    assert len(new_graph.edges) == 3


def test_high_centrality_edges_deterministic():
    graph = _toy_graph()
    g1, m1 = high_centrality_edges(graph, severity=0.4, seed=9)
    g2, m2 = high_centrality_edges(graph, severity=0.4, seed=9)
    assert g1.edges == g2.edges
    assert m1.removed_edges == m2.removed_edges


def test_stale_symbol_refs_points_at_nonexistent_node():
    graph = _toy_graph()
    new_graph, manifest = stale_symbol_refs(graph, severity=0.5, seed=2)
    assert len(manifest.rewired_edges) > 0
    node_ids = graph.node_ids()
    for _old, new_edge in manifest.rewired_edges:
        assert new_edge.dst not in node_ids  # dangling: points at nothing real
    for e in new_graph.edges:
        if e in manifest.rewired_edges:
            continue
    assert len(new_graph.edges) == len(graph.edges)  # edge count preserved, just redirected


def test_stale_symbol_refs_deterministic():
    graph = _toy_graph()
    g1, m1 = stale_symbol_refs(graph, severity=0.3, seed=4)
    g2, m2 = stale_symbol_refs(graph, severity=0.3, seed=4)
    assert g1.edges == g2.edges
    assert m1.rewired_edges == m2.rewired_edges
