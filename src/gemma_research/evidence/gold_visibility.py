"""Detect when a corruption operator's hidden-node set overlaps a task's
gold answer set.

`node_omission` (`evidence/perturb.py`) deliberately leaves
`LocalizationTask.gold_node_ids` untouched when it hides a fraction of
nodes from retrieval; its own docstring says callers "must separately
detect when a hidden node was gold ... rather than silently dropping
those tasks." This module is that detection logic, factored out so it can
be unit-tested on its own and reused by any experiment script that runs
`node_omission` (or a future node-hiding operator with the same contract),
instead of being re-derived ad hoc per script.

A task whose gold node(s) were hidden is not an ordinary retrieval miss:
no ranking function can find an answer that is not in the candidate pool
at all, so conflating the two would misattribute a pool-construction
artefact to retrieval-method weakness.
"""

from __future__ import annotations


def gold_hidden_ids(gold_node_ids: frozenset[str], hidden_node_ids: frozenset[str]) -> frozenset[str]:
    """The subset of `gold_node_ids` that fall inside `hidden_node_ids`."""
    return frozenset(gold_node_ids) & frozenset(hidden_node_ids)


def any_gold_hidden(gold_node_ids: frozenset[str], hidden_node_ids: frozenset[str]) -> bool:
    """True if at least one of the task's gold node ids was hidden."""
    return bool(gold_hidden_ids(gold_node_ids, hidden_node_ids))


def gold_hidden_fraction(gold_node_ids: frozenset[str], hidden_node_ids: frozenset[str]) -> float:
    """Fraction of the task's gold node ids that were hidden.

    Returns 0.0 for a task with no gold ids at all, rather than raising,
    since "no gold ids were hidden" is a true (if vacuous) statement about
    an empty set.
    """
    if not gold_node_ids:
        return 0.0
    return len(gold_hidden_ids(gold_node_ids, hidden_node_ids)) / len(gold_node_ids)
