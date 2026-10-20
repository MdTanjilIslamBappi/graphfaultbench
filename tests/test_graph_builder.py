from pathlib import Path

from gemma_research.data.graph_builder import build_graph_from_source


def _write_toy_repo(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "util.py").write_text(
        '''"""Utility helpers."""


def helper(x):
    """Does a thing."""
    return x + 1
'''
    )
    (root / "pkg" / "service.py").write_text(
        '''from pkg.util import helper


class Service:
    """Service does the main work."""

    def run(self, x):
        """Runs the service."""
        return helper(x) + self.finish(x)

    def finish(self, x):
        return x
'''
    )


def test_build_graph_produces_loc_bench_style_node_ids(tmp_path: Path):
    _write_toy_repo(tmp_path)
    graph, report = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    node_ids = graph.node_ids()
    assert "pkg/util.py:helper" in node_ids
    assert "pkg/service.py:Service" in node_ids
    assert "pkg/service.py:Service.run" in node_ids
    assert "pkg/service.py:Service.finish" in node_ids
    assert report.n_files_skipped == 0
    assert report.n_files_parsed == 3


def test_build_graph_adds_contains_and_calls_edges(tmp_path: Path):
    _write_toy_repo(tmp_path)
    graph, _ = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    edge_pairs = {(e.src, e.dst, e.edge_type) for e in graph.edges}
    assert ("pkg/service.py:Service", "pkg/service.py:Service.run", "contains") in edge_pairs
    assert ("pkg/service.py:Service.run", "pkg/service.py:Service.finish", "calls") in edge_pairs
    assert ("pkg/service.py:Service.run", "pkg/util.py:helper", "calls") in edge_pairs


def test_build_graph_adds_import_edge(tmp_path: Path):
    _write_toy_repo(tmp_path)
    graph, _ = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    import_edges = {(e.src, e.dst) for e in graph.edges if e.edge_type == "imports"}
    assert ("pkg/service.py:<module>", "pkg/util.py:<module>") in import_edges


def test_build_graph_skips_unparseable_file(tmp_path: Path):
    _write_toy_repo(tmp_path)
    (tmp_path / "pkg" / "broken.py").write_text("def broken(:\n    pass\n")
    graph, report = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    assert report.n_files_skipped == 1
    assert "pkg/broken.py:<module>" not in graph.node_ids()


def test_build_graph_collapses_overload_stubs_to_one_node(tmp_path: Path):
    # Real-world repositories commonly define @typing.overload stub
    # signatures that share the implementation's qualified name (PEP 484).
    # Before the fix, each stub produced its own Node with an identical
    # node_id, so graph.nodes had more entries than there were distinct
    # addressable symbols — confirmed on real data in research/node_removal_operator.md
    # (37 duplicated ids / 77 excess node objects on one PrefectHQ/prefect
    # commit). Exactly one Node must now exist per id, and it must be the
    # real implementation (last definition), not a stub.
    (tmp_path / "mod.py").write_text(
        '''import typing


@typing.overload
def convert(x: int) -> int: ...
@typing.overload
def convert(x: str) -> str: ...
def convert(x):
    """Converts x, the real implementation."""
    return x
'''
    )
    graph, report = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    node_ids = [n.node_id for n in graph.nodes]
    assert node_ids.count("mod.py:convert") == 1
    assert len(node_ids) == len(set(node_ids))
    convert_node = next(n for n in graph.nodes if n.node_id == "mod.py:convert")
    assert "real implementation" in convert_node.text
    assert report.n_duplicate_ids_collapsed == 2


def test_build_graph_collapses_same_name_redefinition_keeping_last(tmp_path: Path):
    # A genuine same-name redefinition later in a file (not an @overload
    # stub) must also collapse to a single node — matching Python's own
    # last-binding-wins name resolution, since the earlier definition is
    # unreachable by that name at runtime.
    (tmp_path / "mod.py").write_text(
        '''class Widget:
    """The old, superseded Widget."""


class Widget:
    """The real, final Widget."""
'''
    )
    graph, report = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    node_ids = [n.node_id for n in graph.nodes]
    assert node_ids.count("mod.py:Widget") == 1
    widget_node = next(n for n in graph.nodes if n.node_id == "mod.py:Widget")
    assert "real, final" in widget_node.text
    assert report.n_duplicate_ids_collapsed == 1


def test_build_graph_edges_have_no_exact_duplicates(tmp_path: Path):
    (tmp_path / "mod.py").write_text(
        '''class Widget:
    def run(self):
        pass


class Widget:
    def run(self):
        pass
'''
    )
    graph, _ = build_graph_from_source("owner/toy", "deadbeef", tmp_path)
    edge_list = list(graph.edges)
    assert len(edge_list) == len(set(edge_list))
