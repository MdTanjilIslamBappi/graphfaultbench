"""Deterministic, logged structural-graph corruption operators.

Every operator takes a `CodeGraph` and a seed and returns a new
`CodeGraph` plus a manifest describing exactly what changed, so every run
is reproducible and auditable. Operators never touch node text/answer
labels — only the edge set (and, for node omission, which nodes are
visible to retrieval) — matching the no-leakage requirement in
`Gemma4_Research_Contingency_v2.md` section "Data and experimental protocol".
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from gemma_research.data.types import CodeGraph, Edge


def _stable_seed(seed: int, label: str) -> int:
    """Deterministic sub-seed. `hash(str)` is per-process-randomized in CPython
    (PYTHONHASHSEED), so it must never be used where reproducibility matters."""
    digest = hashlib.sha256(f"{seed}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass(frozen=True)
class PerturbationManifest:
    operator: str
    seed: int
    severity: float
    removed_edges: tuple[Edge, ...] = ()
    hidden_node_ids: frozenset[str] = frozenset()
    rewired_edges: tuple[tuple[Edge, Edge], ...] = ()  # (old, new) pairs


def missing_edges(graph: CodeGraph, severity: float, seed: int) -> tuple[CodeGraph, PerturbationManifest]:
    """Remove a fixed fraction of edges, stratified by edge_type, with a fixed seed."""
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")
    by_type: dict[str, list[Edge]] = {}
    for e in graph.edges:
        by_type.setdefault(e.edge_type, []).append(e)

    removed: list[Edge] = []
    kept: list[Edge] = []
    for edge_type in sorted(by_type):
        ordered = sorted(by_type[edge_type], key=lambda e: (e.src, e.dst))
        rng_local = random.Random(_stable_seed(seed, edge_type))
        rng_local.shuffle(ordered)
        n_remove = round(len(ordered) * severity)
        removed.extend(ordered[:n_remove])
        kept.extend(ordered[n_remove:])

    new_graph = CodeGraph(repo=graph.repo, commit=graph.commit, nodes=graph.nodes, edges=tuple(kept))
    manifest = PerturbationManifest(
        operator="missing_edges", seed=seed, severity=severity, removed_edges=tuple(removed)
    )
    return new_graph, manifest


def node_omission(graph: CodeGraph, severity: float, seed: int) -> tuple[CodeGraph, PerturbationManifest]:
    """Hide a fixed fraction of nodes (and their incident edges) from retrieval.

    Answer labels (`LocalizationTask.gold_node_ids`) are left untouched by
    design: callers must separately detect when a hidden node was gold, to
    measure "the true answer was removed from the candidate set" as the
    playbook requires, rather than silently dropping those tasks.
    """
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")
    ordered_ids = sorted(n.node_id for n in graph.nodes)
    rng = random.Random(seed)
    rng.shuffle(ordered_ids)
    n_hide = round(len(ordered_ids) * severity)
    hidden = frozenset(ordered_ids[:n_hide])

    kept_nodes = tuple(n for n in graph.nodes if n.node_id not in hidden)
    kept_edges = tuple(e for e in graph.edges if e.src not in hidden and e.dst not in hidden)
    new_graph = CodeGraph(repo=graph.repo, commit=graph.commit, nodes=kept_nodes, edges=kept_edges)
    manifest = PerturbationManifest(
        operator="node_omission", seed=seed, severity=severity, hidden_node_ids=hidden
    )
    return new_graph, manifest


def stale_rewire(graph: CodeGraph, severity: float, seed: int) -> tuple[CodeGraph, PerturbationManifest]:
    """Rewire a bounded fraction of edges to a different same-type-node target.

    Synthetic proxy for stale indexes (see playbook C3) — NOT an assertion
    that this matches real-world index drift.
    """
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")
    rng = random.Random(seed)
    kind_by_id = {n.node_id: n.kind for n in graph.nodes}
    nodes_by_kind: dict[str, list[str]] = {}
    for n in graph.nodes:
        nodes_by_kind.setdefault(n.kind, []).append(n.node_id)

    ordered_edges = sorted(graph.edges, key=lambda e: (e.src, e.dst, e.edge_type))
    n_rewire = round(len(ordered_edges) * severity)
    rewire_targets = rng.sample(range(len(ordered_edges)), k=min(n_rewire, len(ordered_edges)))
    rewire_set = set(rewire_targets)

    new_edges: list[Edge] = []
    pairs: list[tuple[Edge, Edge]] = []
    for i, e in enumerate(ordered_edges):
        if i not in rewire_set:
            new_edges.append(e)
            continue
        dst_kind = kind_by_id.get(e.dst, "")
        candidates = [nid for nid in nodes_by_kind.get(dst_kind, []) if nid != e.dst]
        if not candidates:
            new_edges.append(e)
            continue
        new_dst = rng.choice(sorted(candidates))
        new_edge = Edge(src=e.src, dst=new_dst, edge_type=e.edge_type)
        new_edges.append(new_edge)
        pairs.append((e, new_edge))

    new_graph = CodeGraph(repo=graph.repo, commit=graph.commit, nodes=graph.nodes, edges=tuple(new_edges))
    manifest = PerturbationManifest(
        operator="stale_rewire", seed=seed, severity=severity, rewired_edges=tuple(pairs)
    )
    return new_graph, manifest


def high_centrality_edges(graph: CodeGraph, severity: float, seed: int) -> tuple[CodeGraph, PerturbationManifest]:
    """Remove the top `severity` fraction of edges ranked by endpoint degree.

    Degree sum (deg(src) + deg(dst)) is used as a cheap, deterministic proxy
    for "centrality" — true betweenness centrality is O(V*E) and not needed
    to model "the most load-bearing edges are the ones that go missing
    first," which is the scenario this operator targets (directive §2).
    `seed` only breaks ties deterministically; it does not add randomness to
    which edges are *eligible* for removal.
    """
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")
    degree: dict[str, int] = {}
    for e in graph.edges:
        degree[e.src] = degree.get(e.src, 0) + 1
        degree[e.dst] = degree.get(e.dst, 0) + 1

    rng = random.Random(_stable_seed(seed, "high_centrality_tiebreak"))
    scored = [(degree.get(e.src, 0) + degree.get(e.dst, 0), rng.random(), e) for e in graph.edges]
    scored.sort(key=lambda t: (-t[0], t[1]))
    n_remove = round(len(scored) * severity)
    removed = tuple(e for _, _, e in scored[:n_remove])
    kept = tuple(e for _, _, e in scored[n_remove:])

    new_graph = CodeGraph(repo=graph.repo, commit=graph.commit, nodes=graph.nodes, edges=kept)
    manifest = PerturbationManifest(
        operator="high_centrality_edges", seed=seed, severity=severity, removed_edges=removed
    )
    return new_graph, manifest


_DANGLING_PREFIX = "__DANGLING__:"


def stale_symbol_refs(graph: CodeGraph, severity: float, seed: int) -> tuple[CodeGraph, PerturbationManifest]:
    """Redirect a fraction of edges to point at a symbol id that no longer
    exists in the current node set (`__DANGLING__:<original target>`),
    modeling a stale/out-of-date index pointing at a symbol that has since
    moved or been deleted — distinct from `missing_edges` (edge deleted
    entirely) and `stale_rewire` (edge misdirected to a different *real*
    node). Nodes and node text are never touched.
    """
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity must be in [0, 1], got {severity}")
    ordered_edges = sorted(graph.edges, key=lambda e: (e.src, e.dst, e.edge_type))
    rng = random.Random(_stable_seed(seed, "stale_symbol_refs"))
    n_affect = round(len(ordered_edges) * severity)
    affected_idx = set(rng.sample(range(len(ordered_edges)), k=min(n_affect, len(ordered_edges))))

    new_edges: list[Edge] = []
    pairs: list[tuple[Edge, Edge]] = []
    for i, e in enumerate(ordered_edges):
        if i not in affected_idx:
            new_edges.append(e)
            continue
        new_edge = Edge(src=e.src, dst=f"{_DANGLING_PREFIX}{e.dst}", edge_type=e.edge_type)
        new_edges.append(new_edge)
        pairs.append((e, new_edge))

    new_graph = CodeGraph(repo=graph.repo, commit=graph.commit, nodes=graph.nodes, edges=tuple(new_edges))
    manifest = PerturbationManifest(
        operator="stale_symbol_refs", seed=seed, severity=severity, rewired_edges=tuple(pairs)
    )
    return new_graph, manifest
