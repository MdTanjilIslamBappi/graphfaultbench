"""Typed core data structures shared by every retrieval baseline and metric.

A `CodeGraph` models a repository's structural graph (calls/imports/etc.) at
a fixed commit. A `LocalizationTask` pairs a natural-language query with the
set of gold symbol ids that answer it. Nothing here is Kaggle- or
Loc-Bench-specific: `src/gemma_research/data/loaders.py` is responsible for
turning an actual data source into these shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Node:
    node_id: str
    repo: str
    kind: str  # e.g. "function", "class", "module"
    text: str  # symbol name + docstring/snippet used for lexical scoring


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    edge_type: str  # e.g. "calls", "imports", "inherits"


@dataclass(frozen=True)
class CodeGraph:
    repo: str
    commit: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]

    def node_ids(self) -> frozenset[str]:
        return frozenset(n.node_id for n in self.nodes)


@dataclass(frozen=True)
class LocalizationTask:
    task_id: str
    repo: str
    query_text: str
    gold_node_ids: frozenset[str]


@dataclass(frozen=True)
class RankedCandidate:
    node_id: str
    score: float


@dataclass(frozen=True)
class RunResult:
    task_id: str
    method: str
    corruption_label: str
    ranking: tuple[RankedCandidate, ...] = field(default_factory=tuple)
