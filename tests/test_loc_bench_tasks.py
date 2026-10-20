import pandas as pd

from gemma_research.data.loc_bench_tasks import build_tasks_for_commit, is_dev_split
from gemma_research.data.types import CodeGraph, Node


def _graph() -> CodeGraph:
    nodes = (
        Node("pkg/a.py:foo", "owner/toy", "function", "foo does a thing"),
        Node("pkg/b.py:Bar.baz", "owner/toy", "method", "baz does another thing"),
    )
    return CodeGraph(repo="owner/toy", commit="abc", nodes=nodes, edges=())


def test_build_tasks_resolves_matching_gold_ids():
    rows = pd.DataFrame(
        [
            {
                "instance_id": "owner__toy-1",
                "problem_statement": "foo is broken",
                "edit_functions": ["pkg/a.py:foo"],
            }
        ]
    )
    tasks, report = build_tasks_for_commit(rows, _graph(), "owner/toy", "abc")
    assert len(tasks) == 1
    assert tasks[0].gold_node_ids == frozenset({"pkg/a.py:foo"})
    assert report.n_resolved == 1
    assert report.n_excluded == 0


def test_build_tasks_excludes_unresolvable_gold_ids():
    rows = pd.DataFrame(
        [
            {
                "instance_id": "owner__toy-2",
                "problem_statement": "something else is broken",
                "edit_functions": ["pkg/missing.py:nope"],
            }
        ]
    )
    tasks, report = build_tasks_for_commit(rows, _graph(), "owner/toy", "abc")
    assert len(tasks) == 0
    assert report.n_excluded == 1
    assert report.excluded_instance_ids == ("owner__toy-2",)


def test_is_dev_split_deterministic():
    assert is_dev_split("owner__toy-1") == is_dev_split("owner__toy-1")


def test_is_dev_split_respects_fraction_roughly():
    ids = [f"owner__toy-{i}" for i in range(2000)]
    dev_count = sum(1 for i in ids if is_dev_split(i, dev_fraction=0.2))
    assert 300 < dev_count < 500  # roughly 20% of 2000, allowing hash noise
