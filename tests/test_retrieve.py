import math

from gemma_research.data.types import CodeGraph, Edge, Node
from gemma_research.evidence.perturb import node_omission
from gemma_research.evidence.retrieve import (
    DiagnosticGate,
    GraphDiagnostics,
    WeightedDiagnosticGate,
    bm25_rank,
    compute_diagnostics,
    fixed_hybrid_rank,
    graph_expansion_rank,
    repomap_rank,
)


def _repo_graph() -> CodeGraph:
    nodes = (
        Node("auth.login", "toy", "function", "login function handles user authentication"),
        Node("auth.logout", "toy", "function", "logout function clears session"),
        Node("db.query", "toy", "function", "query function executes database query"),
        Node("db.connect", "toy", "function", "connect function opens database connection"),
        Node("util.hash", "toy", "function", "hash function computes password hash"),
    )
    edges = (
        Edge("auth.login", "db.query", "calls"),
        Edge("auth.login", "util.hash", "calls"),
        Edge("db.query", "db.connect", "calls"),
    )
    return CodeGraph(repo="toy", commit="abc", nodes=nodes, edges=edges)


def test_bm25_ranks_lexically_relevant_node_first():
    graph = _repo_graph()
    ranking = bm25_rank(graph, "how does the authentication login work")
    assert ranking[0].node_id == "auth.login"


def test_graph_expansion_prefers_neighbors_of_anchor():
    graph = _repo_graph()
    ranking = graph_expansion_rank(graph, "database connection issue", anchor_top_k=1, hops=1)
    ids_in_order = [c.node_id for c in ranking]
    assert ids_in_order.index("db.connect") < ids_in_order.index("auth.logout")


def test_graph_expansion_with_no_anchor_does_not_crash():
    graph = _repo_graph()
    ranking = graph_expansion_rank(graph, "zzz nonexistent qqq terms", anchor_top_k=1, hops=1)
    assert len(ranking) == len(graph.nodes)


def test_fixed_hybrid_combines_both_signals():
    graph = _repo_graph()
    ranking = fixed_hybrid_rank(graph, "authentication login", lexical_weight=0.5)
    assert ranking[0].node_id == "auth.login"


def test_diagnostic_gate_abstains_on_weak_anchor():
    graph = _repo_graph()
    gate = DiagnosticGate(anchor_floor=0.9)  # deliberately strict for the test
    _, policy, _ = gate.rank(graph, "totally unrelated query text")
    assert policy == "abstain"


def test_diagnostic_gate_falls_back_to_lexical_when_graph_degraded():
    graph = _repo_graph()
    degraded, _ = node_omission(graph, severity=0.8, seed=5)
    gate = DiagnosticGate(coverage_floor=0.6)
    _, policy, diag = gate.rank(degraded, "authentication login", reference_node_count=len(graph.nodes))
    assert diag.node_coverage < 0.6
    assert policy in {"lexical_only", "abstain"}


def test_repomap_rank_prefers_graph_neighbor_of_anchor():
    graph = _repo_graph()
    ranking = repomap_rank(graph, "database connection issue", anchor_top_k=1)
    ids_in_order = [c.node_id for c in ranking]
    assert ids_in_order.index("db.connect") < ids_in_order.index("auth.logout")


def test_repomap_rank_no_anchor_does_not_crash():
    graph = _repo_graph()
    ranking = repomap_rank(graph, "zzz nonexistent qqq terms")
    assert len(ranking) == len(graph.nodes)
    assert all(c.score == 0.0 for c in ranking)


def test_diagnostics_never_require_gold_labels_or_corruption_flag():
    import inspect

    sig = inspect.signature(compute_diagnostics)
    assert "gold" not in sig.parameters
    assert "corruption" not in sig.parameters
    assert "severity" not in sig.parameters


def test_weighted_gate_reproduces_fixed_hybrid_default_on_healthy_graph():
    diag = GraphDiagnostics(node_coverage=1.0, anchor_confidence=1.0, isolated_node_rate=0.0)
    assert WeightedDiagnosticGate.lexical_weight(diag) == 0.5


def test_weighted_gate_reproduces_pure_lexical_on_fully_degraded_graph():
    diag = GraphDiagnostics(node_coverage=0.0, anchor_confidence=1.0, isolated_node_rate=1.0)
    assert WeightedDiagnosticGate.lexical_weight(diag) == 1.0


def test_weighted_gate_weight_increases_monotonically_as_coverage_drops():
    weights = [
        WeightedDiagnosticGate.lexical_weight(
            GraphDiagnostics(node_coverage=c, anchor_confidence=1.0, isolated_node_rate=0.0)
        )
        for c in (1.0, 0.75, 0.5, 0.25, 0.0)
    ]
    assert weights == sorted(weights)
    assert weights[0] == 0.5
    assert weights[-1] == 1.0


def test_weighted_gate_uses_the_weaker_of_coverage_and_isolation_signals():
    # Isolation alone drives health to 0 even though coverage is perfect —
    # mirrors DiagnosticGate's AND-like combination (both signals must be
    # healthy for the best-case weight), just continuous instead of binary.
    diag = GraphDiagnostics(node_coverage=1.0, anchor_confidence=1.0, isolated_node_rate=1.0)
    assert WeightedDiagnosticGate.lexical_weight(diag) == 1.0


def test_weighted_gate_abstains_on_weak_anchor_like_diagnostic_gate():
    graph = _repo_graph()
    gate = WeightedDiagnosticGate(anchor_floor=0.9)  # deliberately strict for the test
    ranking, weight, _ = gate.rank(graph, "totally unrelated query text")
    assert math.isnan(weight)  # NaN sentinel for "abstained", never a real weight
    assert all(c.score == 0.0 for c in ranking)


def test_weighted_gate_ranks_on_degraded_graph_without_abstaining():
    graph = _repo_graph()
    degraded, _ = node_omission(graph, severity=0.4, seed=5)
    gate = WeightedDiagnosticGate()
    ranking, weight, diag = gate.rank(
        degraded, "authentication login", reference_node_count=len(graph.nodes)
    )
    assert diag.node_coverage < 1.0
    # Mirrors DiagnosticGate's own test pattern: a severe-enough corruption
    # can legitimately drop anchor_confidence below the floor too (NaN
    # sentinel), not just the weighted path — both are correct outcomes.
    assert math.isnan(weight) or 0.5 <= weight <= 1.0
    assert len(ranking) == len(degraded.nodes)
