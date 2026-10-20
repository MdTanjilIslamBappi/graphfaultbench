"""Retrieval baselines, all operating on identical candidate pools so
comparisons are fair (playbook C4 / contingency doc protocol step 5).

Baselines:
- `bm25_rank`: lexical-only, unaffected by graph quality.
- `graph_expansion_rank`: lexical anchor + bounded graph-neighborhood expansion.
- `fixed_hybrid_rank`: a static weighted blend of the two.
- `DiagnosticGate.rank`: Candidate A's distinguishing idea — choose
  graph-only / lexical-only / hybrid / abstain using only runtime-observable
  signals (graph coverage, anchor confidence), never gold labels or
  corruption flags. See Gemma4_Research_Contingency_v2.md, "Distinguishing
  idea to test".
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

import networkx as nx

from gemma_research.data.types import CodeGraph, Node, RankedCandidate

_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class BM25Index:
    """Minimal, dependency-free BM25 over a fixed corpus of `Node`s.

    Deliberately not using an external BM25 package: the corpus here is a
    handful of short code symbols/docstrings, not a general IR workload, and
    a ~30-line implementation is easier to audit for this project than a
    new dependency.
    """

    def __init__(self, nodes: tuple[Node, ...], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.node_ids = [n.node_id for n in nodes]
        self.doc_tokens = {n.node_id: _tokenize(n.text) for n in nodes}
        self.doc_len = {nid: len(toks) for nid, toks in self.doc_tokens.items()}
        self.avg_len = (sum(self.doc_len.values()) / len(self.doc_len)) if self.doc_len else 0.0
        self.df: Counter[str] = Counter()
        for toks in self.doc_tokens.values():
            for term in set(toks):
                self.df[term] += 1
        self.n_docs = len(nodes)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def score(self, query_text: str) -> dict[str, float]:
        query_terms = _tokenize(query_text)
        scores: dict[str, float] = {nid: 0.0 for nid in self.node_ids}
        if self.n_docs == 0:
            return scores
        for nid in self.node_ids:
            tf = Counter(self.doc_tokens[nid])
            dl = self.doc_len[nid] or 1
            total = 0.0
            for term in query_terms:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                idf = self._idf(term)
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avg_len or 1))
                total += idf * (f * (self.k1 + 1)) / denom
            scores[nid] = total
        return scores


def bm25_rank(
    graph: CodeGraph, query_text: str, index: BM25Index | None = None
) -> tuple[RankedCandidate, ...]:
    """`index` lets a caller reuse a BM25Index across many calls sharing the
    same node set (e.g. the same task re-scored under different edge-level
    corruptions) instead of re-tokenizing every node's text each time — pure
    performance optimization, identical scores either way."""
    index = index or BM25Index(graph.nodes)
    scores = index.score(query_text)
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return tuple(RankedCandidate(node_id=nid, score=s) for nid, s in ranked)


def _neighbors(graph: CodeGraph) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {n.node_id: set() for n in graph.nodes}
    for e in graph.edges:
        adjacency.setdefault(e.src, set()).add(e.dst)
        adjacency.setdefault(e.dst, set()).add(e.src)
    return adjacency


def graph_expansion_rank(
    graph: CodeGraph,
    query_text: str,
    anchor_top_k: int = 3,
    hops: int = 1,
    bm25_index: BM25Index | None = None,
) -> tuple[RankedCandidate, ...]:
    """Seed from the top-k lexical anchors, then rank by shortest graph distance."""
    anchors = bm25_rank(graph, query_text, index=bm25_index)[:anchor_top_k]
    anchor_ids = [a.node_id for a in anchors if a.score > 0]
    adjacency = _neighbors(graph)

    if not anchor_ids:
        # No useful anchor: behaviour is explicitly defined (playbook C4 #2)
        # as falling back to an empty/uniform ranking rather than guessing.
        return tuple(RankedCandidate(node_id=n.node_id, score=0.0) for n in graph.nodes)

    distance: dict[str, int] = {aid: 0 for aid in anchor_ids}
    frontier = set(anchor_ids)
    for depth in range(1, hops + 1):
        next_frontier: set[str] = set()
        for nid in frontier:
            for nbr in adjacency.get(nid, ()):
                if nbr not in distance:
                    distance[nbr] = depth
                    next_frontier.add(nbr)
        frontier = next_frontier
        if not frontier:
            break

    max_dist = hops + 1
    scored = [
        RankedCandidate(node_id=n.node_id, score=1.0 / (1 + distance.get(n.node_id, max_dist)))
        for n in graph.nodes
    ]
    return tuple(sorted(scored, key=lambda c: (-c.score, c.node_id)))


def _normalize(ranking: tuple[RankedCandidate, ...]) -> dict[str, float]:
    scores = {c.node_id: c.score for c in ranking}
    max_score = max(scores.values(), default=0.0)
    if max_score <= 0:
        return {nid: 0.0 for nid in scores}
    return {nid: s / max_score for nid, s in scores.items()}


def fixed_hybrid_rank(
    graph: CodeGraph,
    query_text: str,
    lexical_weight: float = 0.5,
    bm25_index: BM25Index | None = None,
) -> tuple[RankedCandidate, ...]:
    lexical = _normalize(bm25_rank(graph, query_text, index=bm25_index))
    graph_scores = _normalize(graph_expansion_rank(graph, query_text, bm25_index=bm25_index))
    combined = {
        nid: lexical_weight * lexical.get(nid, 0.0) + (1 - lexical_weight) * graph_scores.get(nid, 0.0)
        for nid in lexical
    }
    ranked = sorted(combined.items(), key=lambda kv: (-kv[1], kv[0]))
    return tuple(RankedCandidate(node_id=nid, score=s) for nid, s in ranked)


def repomap_rank(
    graph: CodeGraph, query_text: str, anchor_top_k: int = 3, bm25_index: BM25Index | None = None
) -> tuple[RankedCandidate, ...]:
    """Structural-importance baseline: personalized PageRank over the
    directed graph, seeded (personalized) by BM25 lexical anchors.

    This is our own reimplementation of the *idea* behind aider's RepoMap
    (rank-by-structural-centrality-near-what-the-query-touches) — not the
    original tool, not its exact algorithm, and not claimed to reproduce its
    published numbers. Included so Candidate A's hybrid/gate baselines are
    compared against a published structural-ranking idea, not only against
    baselines built for this project (directive §3).
    """
    anchors = bm25_rank(graph, query_text, index=bm25_index)[:anchor_top_k]
    anchor_scores = {a.node_id: a.score for a in anchors if a.score > 0}
    if not anchor_scores:
        return tuple(RankedCandidate(node_id=n.node_id, score=0.0) for n in graph.nodes)

    g = nx.DiGraph()
    g.add_nodes_from(n.node_id for n in graph.nodes)
    g.add_edges_from((e.src, e.dst) for e in graph.edges)
    total = sum(anchor_scores.values())
    personalization = {nid: s / total for nid, s in anchor_scores.items()}
    try:
        pr = nx.pagerank(g, alpha=0.85, personalization=personalization, dangling=personalization)
    except nx.PowerIterationFailedConvergence:
        pr = {nid: 0.0 for nid in g.nodes}
    ranked = sorted(pr.items(), key=lambda kv: (-kv[1], kv[0]))
    return tuple(RankedCandidate(node_id=nid, score=s) for nid, s in ranked)


@dataclass(frozen=True)
class GraphDiagnostics:
    """Runtime-observable signals only — never corruption flags or gold labels."""

    node_coverage: float  # fraction of expected node set actually present (proxy; see note below)
    anchor_confidence: float  # top lexical anchor score, normalized
    isolated_node_rate: float  # fraction of nodes with zero edges


def compute_diagnostics(
    graph: CodeGraph,
    query_text: str,
    reference_node_count: int | None = None,
    bm25_index: BM25Index | None = None,
) -> GraphDiagnostics:
    """`reference_node_count` is a deployment-time constant (e.g. a prior
    snapshot's node count), NOT the gold answer set or corruption severity —
    using the current eval severity here would leak the corruption label."""
    index = bm25_index or BM25Index(graph.nodes)
    scores = index.score(query_text)
    top_score = max(scores.values(), default=0.0)
    anchor_confidence = min(1.0, top_score / 10.0)  # bounded heuristic normalization

    adjacency = _neighbors(graph)
    n_nodes = len(graph.nodes) or 1
    isolated = sum(1 for nid in adjacency if not adjacency[nid])
    isolated_rate = isolated / n_nodes

    if reference_node_count and reference_node_count > 0:
        coverage = min(1.0, len(graph.nodes) / reference_node_count)
    else:
        coverage = 1.0
    return GraphDiagnostics(
        node_coverage=coverage, anchor_confidence=anchor_confidence, isolated_node_rate=isolated_rate
    )


class DiagnosticGate:
    """Candidate A's distinguishing idea: pick a policy from observable
    diagnostics instead of a single fixed hybrid weight or threshold.

    Thresholds are development-tunable constants, never fit on the held-out
    evaluation set (contingency doc protocol step 4).
    """

    def __init__(
        self,
        coverage_floor: float = 0.6,
        isolated_ceiling: float = 0.5,
        anchor_floor: float = 0.1,
    ) -> None:
        self.coverage_floor = coverage_floor
        self.isolated_ceiling = isolated_ceiling
        self.anchor_floor = anchor_floor

    def choose_policy(self, diag: GraphDiagnostics) -> str:
        if diag.anchor_confidence < self.anchor_floor:
            return "abstain"
        graph_reliable = diag.node_coverage >= self.coverage_floor and diag.isolated_node_rate <= self.isolated_ceiling
        if graph_reliable:
            return "hybrid"
        return "lexical_only"

    def rank(
        self,
        graph: CodeGraph,
        query_text: str,
        reference_node_count: int | None = None,
        bm25_index: BM25Index | None = None,
    ) -> tuple[tuple[RankedCandidate, ...], str, GraphDiagnostics]:
        diag = compute_diagnostics(graph, query_text, reference_node_count, bm25_index=bm25_index)
        policy = self.choose_policy(diag)
        if policy == "abstain":
            return tuple(RankedCandidate(node_id=n.node_id, score=0.0) for n in graph.nodes), policy, diag
        if policy == "lexical_only":
            return bm25_rank(graph, query_text, index=bm25_index), policy, diag
        return fixed_hybrid_rank(graph, query_text, bm25_index=bm25_index), policy, diag


class WeightedDiagnosticGate:
    """A continuously-weighted variant of `DiagnosticGate`, replacing its
    binary hybrid/lexical_only switch with a smooth ramp over the same two
    signals — the direction named as future work in
    `paper/manuscript.md` section 7 ("a learned or continuously-weighted
    combination of the three diagnostic signals, rather than a single
    binary-threshold gate"), built and tested here rather than left
    unactioned, per the adversarial-challenge finding in
    `research/kaggle_judging_simulation.md` section 2 item 4.

    `anchor_confidence`'s role is unchanged from `DiagnosticGate`: it is
    about query/lexical-match quality, not graph degradation, so abstention
    stays a hard gate on that signal alone — only the coverage/isolation-
    driven policy choice is generalised to a continuous weight, to isolate
    exactly the mechanism the challenge targeted.

    Design, stated explicitly for reproducibility: `health =
    min(node_coverage, 1 - isolated_node_rate)` reuses `DiagnosticGate`'s
    own AND-like combination of its two graph-quality signals (both had to
    clear their threshold for "hybrid"; here, the weaker of the two drives
    the ramp instead). `lexical_weight = 1 - 0.5 * health` is the simplest
    monotonic map with the two properties that make it a direct
    generalisation, not a different heuristic: at `health = 1` (a fully
    healthy graph) it reproduces `fixed_hybrid_rank`'s own default 0.5/0.5
    weighting exactly, and at `health = 0` (fully degraded) it reproduces
    pure `bm25_rank` exactly — the same two extremes `DiagnosticGate`
    switches between, now connected by a ramp instead of a step. No part of
    this formula is fit on evaluation data; it is fixed before any row of
    this experiment is scored, the same discipline already applied to
    `DiagnosticGate`'s own thresholds.
    """

    def __init__(self, anchor_floor: float = 0.1) -> None:
        self.anchor_floor = anchor_floor

    @staticmethod
    def lexical_weight(diag: GraphDiagnostics) -> float:
        health = min(diag.node_coverage, 1.0 - diag.isolated_node_rate)
        health = max(0.0, min(1.0, health))
        return 1.0 - 0.5 * health

    def rank(
        self,
        graph: CodeGraph,
        query_text: str,
        reference_node_count: int | None = None,
        bm25_index: BM25Index | None = None,
    ) -> tuple[tuple[RankedCandidate, ...], float, GraphDiagnostics]:
        diag = compute_diagnostics(graph, query_text, reference_node_count, bm25_index=bm25_index)
        if diag.anchor_confidence < self.anchor_floor:
            empty = tuple(RankedCandidate(node_id=n.node_id, score=0.0) for n in graph.nodes)
            return empty, float("nan"), diag
        weight = self.lexical_weight(diag)
        ranking = fixed_hybrid_rank(graph, query_text, lexical_weight=weight, bm25_index=bm25_index)
        return ranking, weight, diag
