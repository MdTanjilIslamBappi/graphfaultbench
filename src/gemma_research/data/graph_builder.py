"""Build a `CodeGraph` from a real Python repository snapshot via static
analysis only (Python `ast`), scoped to the constructs we actually need:
module/class/function/method nodes, and `contains`/`calls`/`imports` edges.

Node ids use the exact `relative/path.py:Qualified.Name` convention used by
Loc-Bench V1's `edit_functions`/`added_functions` columns (confirmed by
inspecting the dataset directly — see `research/decision_log.md`), so gold
labels resolve against this graph by exact string match, with no fuzzy
matching step that could silently paper over a mismatch.

Known, documented limitations (see `research/limitations.md`):
- Call-edge resolution is name-based, not type-aware: `obj.method()` is
  matched to a method node by its *unqualified* name, preferring same-file
  candidates, falling back to a deterministic repo-wide pick. This will
  create some false edges and miss some true ones. It is a static-analysis
  heuristic, not a claim of correctness.
- Only `.py` files are parsed. Files with syntax errors (e.g. Python 2 only
  source, if any) are skipped and counted in `GraphBuildReport`.
- Import resolution only follows imports that resolve to a file inside the
  same snapshot; external-package imports are not added as edges.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from gemma_research.data.types import CodeGraph, Edge, Node

_SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclass(frozen=True)
class GraphBuildReport:
    repo: str
    commit: str
    n_files_parsed: int
    n_files_skipped: int
    n_nodes: int
    n_edges: int
    n_unresolved_calls: int
    n_duplicate_ids_collapsed: int


def _relpath(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _direct_calls(scope_node: ast.AST) -> list[ast.Call]:
    """Calls made directly in `scope_node`'s body, not inside a nested def/class."""
    calls: list[ast.Call] = []

    def walk(node: ast.AST, is_root: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Call):
                calls.append(child)
            if isinstance(child, _SCOPE_TYPES) and not is_root:
                continue
            walk(child, False)

    walk(scope_node, True)
    return calls


def _call_target_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _source_segment_from_lines(lines: list[str], node: ast.AST) -> str:
    """Equivalent to `ast.get_source_segment(source, node)`, but takes
    pre-split lines instead of the raw source string.

    `ast.get_source_segment` re-splits the *entire* file on every call (via
    the private `ast._splitlines_no_ff`); calling it once per AST node in a
    large file made graph construction effectively quadratic in file size
    (profiled at ~300s of a ~320s build for a ~9.4k-node repository). This
    does the same slicing against a lines list computed once per file.

    Uses plain `str.splitlines()` rather than `ast._splitlines_no_ff`, so it
    differs only for source containing form-feed characters — not relevant
    to the real Python source this project processes.
    """
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    col_offset = getattr(node, "col_offset", None)
    end_col_offset = getattr(node, "end_col_offset", None)
    if lineno is None or end_lineno is None or col_offset is None or end_col_offset is None:
        return ""
    lineno -= 1
    end_lineno -= 1
    if end_lineno == lineno:
        return lines[lineno].encode()[col_offset:end_col_offset].decode()
    first = lines[lineno][col_offset:]
    middle = lines[lineno + 1 : end_lineno]
    last = lines[end_lineno][:end_col_offset]
    return "\n".join([first, *middle, last])


def _docstring_or_snippet(node: ast.AST, lines: list[str]) -> str:
    doc = ast.get_docstring(node) or ""
    segment = _source_segment_from_lines(lines, node)
    text = f"{doc}\n{segment}".strip()
    return text[:2000]


class _FileVisitor:
    def __init__(self, repo: str, relpath: str, source: str) -> None:
        self.repo = repo
        self.relpath = relpath
        self.source = source
        self.lines = source.splitlines()
        self.nodes: list[Node] = []
        self.contains_edges: list[Edge] = []
        self.pending_calls: list[tuple[str, list[ast.Call]]] = []  # (owner_node_id, calls)
        self.module_id = f"{relpath}:<module>"
        self.tree: ast.Module | None = None

    def visit_module(self, tree: ast.Module) -> None:
        self.nodes.append(Node(self.module_id, self.repo, "module", _docstring_or_snippet(tree, self.lines)))
        for child in tree.body:
            if isinstance(child, ast.ClassDef):
                self._visit_class(child, parent_id=self.module_id, qualname_prefix="")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(child, parent_id=self.module_id, qualname_prefix="", kind="function")

    def _visit_class(self, node: ast.ClassDef, parent_id: str, qualname_prefix: str) -> None:
        qualname = f"{qualname_prefix}{node.name}"
        node_id = f"{self.relpath}:{qualname}"
        self.nodes.append(Node(node_id, self.repo, "class", _docstring_or_snippet(node, self.lines)))
        self.contains_edges.append(Edge(parent_id, node_id, "contains"))
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                self._visit_class(child, parent_id=node_id, qualname_prefix=f"{qualname}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(child, parent_id=node_id, qualname_prefix=f"{qualname}.", kind="method")

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent_id: str, qualname_prefix: str, kind: str
    ) -> None:
        qualname = f"{qualname_prefix}{node.name}"
        node_id = f"{self.relpath}:{qualname}"
        self.nodes.append(Node(node_id, self.repo, kind, _docstring_or_snippet(node, self.lines)))
        self.contains_edges.append(Edge(parent_id, node_id, "contains"))
        self.pending_calls.append((node_id, _direct_calls(node)))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                self._visit_class(child, parent_id=node_id, qualname_prefix=f"{qualname}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(child, parent_id=node_id, qualname_prefix=f"{qualname}.", kind="function")


def _resolve_import_target(
    module_relpath: str, module_name_dotted: str, is_relative: bool, level: int, all_module_ids: set[str]
) -> str | None:
    if is_relative:
        base_parts = module_relpath.rsplit("/", 1)[0].split("/") if "/" in module_relpath else []
        for _ in range(max(level - 1, 0)):
            if base_parts:
                base_parts.pop()
        parts = base_parts + (module_name_dotted.split(".") if module_name_dotted else [])
    else:
        parts = module_name_dotted.split(".")
    for candidate in (
        "/".join(parts) + ".py",
        "/".join([*parts, "__init__.py"]),
    ):
        module_id = f"{candidate}:<module>"
        if module_id in all_module_ids:
            return module_id
    return None


def build_graph_from_source(repo: str, commit: str, source_root: Path) -> tuple[CodeGraph, GraphBuildReport]:
    py_files = sorted(p for p in source_root.rglob("*.py") if p.is_file())

    visitors: list[_FileVisitor] = []
    n_skipped = 0
    for path in py_files:
        relpath = _relpath(path, source_root)
        try:
            source = path.read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(source, filename=relpath)
        except (SyntaxError, UnicodeDecodeError, ValueError):
            n_skipped += 1
            continue
        visitor = _FileVisitor(repo, relpath, source)
        visitor.tree = tree
        visitor.visit_module(tree)
        visitors.append(visitor)

    all_edges: list[Edge] = []
    by_simple_name: dict[str, list[str]] = {}
    by_file_simple_name: dict[str, dict[str, list[str]]] = {}
    module_ids: set[str] = set()

    # A repository can legitimately define more than one node under the
    # same id: the dominant case observed in practice is a `@typing.overload`
    # stub sharing its implementation's qualified name (PEP 484 convention:
    # the real implementation is the *last* `def` of that name in the file);
    # the rarer case is a genuine same-name redefinition later in the file,
    # which Python's own name resolution also resolves to the later
    # binding. Loc-Bench V1 gold labels address a node by this exact id
    # string (module docstring above), so the graph must expose exactly one
    # Node per id - otherwise `node_coverage` and the node-hiding corruption
    # operators (`evidence/perturb.py::node_omission`) silently operate over
    # more "node objects" than there are distinct addressable symbols. Kept:
    # the last definition in file order, consistent with both cases above.
    n_raw_nodes = 0
    node_by_id: dict[str, Node] = {}
    for v in visitors:
        module_ids.add(v.module_id)
        n_raw_nodes += len(v.nodes)
        for n in v.nodes:
            node_by_id[n.node_id] = n
        all_edges.extend(v.contains_edges)

    all_nodes = list(node_by_id.values())
    n_duplicate_ids_collapsed = n_raw_nodes - len(all_nodes)
    for n in all_nodes:
        if n.kind in ("function", "method", "class"):
            simple = n.node_id.rsplit(":", 1)[1].rsplit(".", 1)[-1]
            relpath = n.node_id.split(":", 1)[0]
            by_simple_name.setdefault(simple, []).append(n.node_id)
            by_file_simple_name.setdefault(relpath, {}).setdefault(simple, []).append(n.node_id)

    # Sort each candidate list once up front rather than on every call-site
    # lookup below: with common names (`__init__`, `run`, `get`, ...) shared
    # by hundreds of nodes across a large repo, re-sorting per lookup made
    # this loop quadratic-ish in practice and was the dominant cost of a
    # graph build (measured ~90s for mypy's ~9.4k nodes before this fix).
    by_simple_name = {name: sorted(ids) for name, ids in by_simple_name.items()}
    by_file_simple_name = {
        relpath: {name: sorted(ids) for name, ids in file_map.items()}
        for relpath, file_map in by_file_simple_name.items()
    }

    n_unresolved = 0
    for v in visitors:
        file_index = by_file_simple_name.get(v.relpath, {})
        for owner_id, calls in v.pending_calls:
            for call in calls:
                target_name = _call_target_name(call)
                if target_name is None:
                    continue
                candidates = file_index.get(target_name) or by_simple_name.get(target_name, [])
                candidates = [c for c in candidates if c != owner_id]
                if not candidates:
                    n_unresolved += 1
                    continue
                all_edges.append(Edge(owner_id, candidates[0], "calls"))

    for v in visitors:
        # Reuse the tree parsed in the first pass instead of re-parsing every
        # file a second time (every file here already parsed cleanly, or it
        # would not have produced a visitor).
        for stmt in ast.walk(v.tree):
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    target = _resolve_import_target(v.relpath, alias.name, False, 0, module_ids)
                    if target:
                        all_edges.append(Edge(v.module_id, target, "imports"))
            elif isinstance(stmt, ast.ImportFrom):
                target = _resolve_import_target(
                    v.relpath, stmt.module or "", stmt.level > 0, stmt.level, module_ids
                )
                if target:
                    all_edges.append(Edge(v.module_id, target, "imports"))

    # Collapsing duplicate nodes above can leave exact-duplicate edges (most
    # commonly two identical `contains` edges from the same parent to a
    # since-collapsed child id); drop them, preserving first-occurrence
    # order, rather than reporting an inflated edge count.
    seen_edges: set[Edge] = set()
    deduped_edges: list[Edge] = []
    for e in all_edges:
        if e not in seen_edges:
            seen_edges.add(e)
            deduped_edges.append(e)
    all_edges = deduped_edges

    graph = CodeGraph(repo=repo, commit=commit, nodes=tuple(all_nodes), edges=tuple(all_edges))
    report = GraphBuildReport(
        repo=repo,
        commit=commit,
        n_files_parsed=len(visitors),
        n_files_skipped=n_skipped,
        n_nodes=len(all_nodes),
        n_edges=len(all_edges),
        n_unresolved_calls=n_unresolved,
        n_duplicate_ids_collapsed=n_duplicate_ids_collapsed,
    )
    return graph, report
