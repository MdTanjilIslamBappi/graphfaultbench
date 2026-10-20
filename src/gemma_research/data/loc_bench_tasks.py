"""Turn real Loc-Bench V1 rows into `LocalizationTask`s against a real,
statically-built repository graph.

Leakage controls (directive §4.1-4.3):
- The query text is `problem_statement` ONLY. `hints_text` (can contain
  fix hints) and `patch`/`test_patch` (the answer itself) are never passed
  to any retriever.
- The graph is built from the source tree at `base_commit`, i.e. BEFORE the
  fix patch is applied, so the retriever cannot see the already-fixed code.
- A task is only "evaluable" if every gold id in `edit_functions` resolves
  by exact string match to a node actually present in that commit's graph.
  Rows that don't resolve are excluded and counted, not silently dropped —
  see `GoldResolutionReport`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd

from gemma_research.data.types import CodeGraph, LocalizationTask


@dataclass(frozen=True)
class GoldResolutionReport:
    repo: str
    commit: str
    n_rows_for_commit: int
    n_resolved: int
    n_excluded: int
    excluded_instance_ids: tuple[str, ...]


def is_dev_split(instance_id: str, dev_fraction: float = 0.2) -> bool:
    """Deterministic, order-independent dev/eval split by instance_id hash.

    Dev rows are set aside for any future gate-threshold tuning; the current
    pilot does NOT tune anything on them (DiagnosticGate keeps its Phase-1
    default thresholds) — see research/limitations.md.
    """
    digest = hashlib.sha256(instance_id.encode()).digest()
    bucket = int.from_bytes(digest[:2], "big") / 65535.0
    return bucket < dev_fraction


def build_tasks_for_commit(
    rows: pd.DataFrame, graph: CodeGraph, repo: str, commit: str
) -> tuple[list[LocalizationTask], GoldResolutionReport]:
    node_ids = graph.node_ids()
    tasks: list[LocalizationTask] = []
    excluded: list[str] = []
    for _, row in rows.iterrows():
        gold = frozenset(row["edit_functions"])
        if not gold or not gold.issubset(node_ids):
            excluded.append(str(row["instance_id"]))
            continue
        tasks.append(
            LocalizationTask(
                task_id=str(row["instance_id"]),
                repo=repo,
                query_text=str(row["problem_statement"]),
                gold_node_ids=gold,
            )
        )
    report = GoldResolutionReport(
        repo=repo,
        commit=commit,
        n_rows_for_commit=len(rows),
        n_resolved=len(tasks),
        n_excluded=len(excluded),
        excluded_instance_ids=tuple(excluded),
    )
    return tasks, report


def load_loc_bench(parquet_path: str, repos: tuple[str, ...]) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)
    return df[df["repo"].isin(repos)].copy()
