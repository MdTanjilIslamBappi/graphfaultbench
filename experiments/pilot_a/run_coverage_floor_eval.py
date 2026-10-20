"""Phase 4 scoped experiment: does switching `DiagnosticGate` to
`lexical_only` under high-severity `node_omission` actually improve
retrieval accuracy over the two simpler baselines (`bm25`, `fixed_hybrid`),
and does this hold on the 40 held-out **eval** tasks, not just the 7 dev
tasks Phase 3 used?

Background: Phase 3 (`experiments/pilot_a/run_node_omission_experiment.py`,
`research/node_removal_operator.md`) showed that `node_omission` makes
`node_coverage` drop below `DiagnosticGate`'s `coverage_floor = 0.6` at
severity >= 0.5, causing the gate to switch from `hybrid` to `lexical_only`
on about half of its 84 dev-split rows. That experiment measured *only*
which policy got chosen, never whether the switch helps retrieval accuracy,
and it was scored on the 7 dev tasks Phase 2 set aside, never the 40 eval
tasks. This script closes both gaps: it scores `bm25_rank`, `fixed_hybrid_rank`,
and `DiagnosticGate().rank(...)` against corrupted graphs on the eval split.

Critical constraint, enforced in code, not just prose: `DiagnosticGate`'s
three thresholds (`coverage_floor`, `isolated_ceiling`, `anchor_floor`) are
asserted against `DiagnosticGate.__init__`'s own default parameter values
(read via `inspect`, not hardcoded blindly) before anything runs. This
script is a validation of those already-fixed, development-time-set
values against previously-unused eval data -- it is NOT a tuning exercise,
and it never changes, sweeps, or fits any threshold.

What this script does NOT do:
- It does not touch, re-run, or modify `results/pilot/` (Phase 2, frozen)
  or `results/node_omission_dev/` (Phase 3, frozen). Its own output goes to
  `results/coverage_floor_eval/`.
- It does not change any `DiagnosticGate` threshold.
- It does not score the 7 dev-split tasks (enforced by assertion: the
  eval-task and dev-task id sets collected while iterating must be
  disjoint, and every scored task id must be an eval-task id).
- It does not reimplement `compute_diagnostics`, `bm25_rank`,
  `fixed_hybrid_rank`, the metric functions, or the gold-visibility
  helpers -- all are imported and called as-is from the existing modules.

Usage: `python experiments/pilot_a/run_coverage_floor_eval.py`
"""

from __future__ import annotations

import csv
import hashlib
import inspect
import json
import resource
import sys
import time
from pathlib import Path

import yaml

from gemma_research.data.graph_builder import build_graph_from_source
from gemma_research.data.loc_bench_tasks import build_tasks_for_commit, is_dev_split, load_loc_bench
from gemma_research.data.repo_source import fetch_repo_snapshot
from gemma_research.data.types import CodeGraph, LocalizationTask
from gemma_research.evidence.gold_visibility import any_gold_hidden, gold_hidden_fraction
from gemma_research.evidence.perturb import node_omission
from gemma_research.evidence.retrieve import BM25Index, DiagnosticGate, bm25_rank, fixed_hybrid_rank
from gemma_research.metrics.scoring import (
    bootstrap_ci_clustered,
    hit_at_k,
    reciprocal_rank,
    strict_acc_at_k,
)

ROOT = Path(__file__).resolve().parents[2]

# Same severities and seeds as configs/pilot_a.yaml / Phase 3. 0.0 is the
# healthy (uncorrupted) control, reusing the convention from
# run_real_pilot.py's `_corruption_combos` and Phase 3's SEVERITIES list.
SEVERITIES = [0.0, 0.25, 0.5, 0.75]

METRIC_NAMES = ("hit_at_1", "hit_at_3", "hit_at_5", "strict_acc_at_5", "mrr")

METHODS = ("bm25", "fixed_hybrid", "diagnostic_gate")


def _assert_gate_thresholds_unchanged() -> DiagnosticGate:
    """Read `DiagnosticGate.__init__`'s own default parameter values (not a
    hardcoded copy of them) and assert both that they equal the values this
    phase's brief states (0.6 / 0.5 / 0.1) and that a freshly constructed
    `DiagnosticGate()` actually carries those values. This fails loudly if
    anyone -- including a future edit to this script -- ever changes the
    defaults, instead of silently validating against a stale expectation.
    """
    sig = inspect.signature(DiagnosticGate.__init__)
    expected_coverage_floor = sig.parameters["coverage_floor"].default
    expected_isolated_ceiling = sig.parameters["isolated_ceiling"].default
    expected_anchor_floor = sig.parameters["anchor_floor"].default

    assert expected_coverage_floor == 0.6, (
        f"DiagnosticGate.__init__'s coverage_floor default is {expected_coverage_floor}, "
        "not 0.6 as this phase's brief assumed -- refusing to proceed without re-reading "
        "the brief's constraint against the real signature."
    )
    assert expected_isolated_ceiling == 0.5, (
        f"DiagnosticGate.__init__'s isolated_ceiling default is {expected_isolated_ceiling}, not 0.5."
    )
    assert expected_anchor_floor == 0.1, (
        f"DiagnosticGate.__init__'s anchor_floor default is {expected_anchor_floor}, not 0.1."
    )

    gate = DiagnosticGate()
    assert gate.coverage_floor == expected_coverage_floor
    assert gate.isolated_ceiling == expected_isolated_ceiling
    assert gate.anchor_floor == expected_anchor_floor
    return gate


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _score_row(
    ranking,
    gold_ids: frozenset[str],
) -> dict[str, float]:
    return {
        "hit_at_1": hit_at_k(ranking, gold_ids, 1),
        "hit_at_3": hit_at_k(ranking, gold_ids, 3),
        "hit_at_5": hit_at_k(ranking, gold_ids, 5),
        "strict_acc_at_5": strict_acc_at_k(ranking, gold_ids, 5),
        "mrr": reciprocal_rank(ranking, gold_ids),
    }


def run(config_path: Path) -> dict:
    gate = _assert_gate_thresholds_unchanged()

    config = yaml.safe_load(config_path.read_text())
    parquet_path = ROOT / config["loc_bench_parquet"]
    dataset_sha256 = _file_sha256(parquet_path)

    df = load_loc_bench(str(parquet_path), tuple(config["repos"]))

    rows: list[dict] = []
    gold_hidden_rows: list[dict] = []
    graph_reports = []
    gold_reports = []
    eval_task_ids: set[str] = set()
    dev_task_ids: set[str] = set()
    excluded_total = 0

    for repo in config["repos"]:
        repo_rows = df[df["repo"] == repo]
        for commit, commit_rows in repo_rows.groupby("base_commit"):
            source_root = fetch_repo_snapshot(repo, commit)
            graph, build_report = build_graph_from_source(repo, commit, source_root)
            graph_reports.append(build_report.__dict__)

            tasks, gold_report = build_tasks_for_commit(commit_rows, graph, repo, commit)
            gold_reports.append(gold_report.__dict__)
            excluded_total += gold_report.n_excluded

            eval_tasks: list[LocalizationTask] = []
            for task in tasks:
                if is_dev_split(task.task_id, config["dev_fraction"]):
                    dev_task_ids.add(task.task_id)
                else:
                    eval_tasks.append(task)
                    eval_task_ids.add(task.task_id)

            if not eval_tasks:
                continue

            reference_node_count = len(graph.nodes)
            for seed in config["seeds"]:
                for severity in SEVERITIES:
                    if severity == 0.0:
                        corrupted: CodeGraph = graph
                        hidden_ids: frozenset[str] = frozenset()
                        operator_name = "healthy_control"
                    else:
                        corrupted, manifest = node_omission(graph, severity, seed)
                        hidden_ids = manifest.hidden_node_ids
                        operator_name = "node_omission"

                    # Fresh BM25Index built from the *current* (possibly
                    # node-reduced) graph, never a cached full-graph index:
                    # node_omission changes the node set, so a stale index
                    # could let a hidden node's text still contribute to
                    # scoring, exactly as Phase 3 reasoned.
                    bm25_index = BM25Index(corrupted.nodes)

                    for task in eval_tasks:
                        hidden = any_gold_hidden(task.gold_node_ids, hidden_ids)
                        hidden_frac = gold_hidden_fraction(task.gold_node_ids, hidden_ids)

                        gold_hidden_rows.append(
                            {
                                "repo": repo,
                                "commit": commit,
                                "task_id": task.task_id,
                                "operator": operator_name,
                                "severity": severity,
                                "seed": seed,
                                "any_gold_hidden": hidden,
                                "gold_hidden_fraction": hidden_frac,
                                "n_gold_ids": len(task.gold_node_ids),
                                "n_hidden_nodes": len(hidden_ids),
                            }
                        )

                        common = {
                            "repo": repo,
                            "commit": commit,
                            "task_id": task.task_id,
                            "operator": operator_name,
                            "severity": severity,
                            "seed": seed,
                            "n_graph_nodes": len(corrupted.nodes),
                            "n_graph_edges": len(corrupted.edges),
                            "n_gold_ids": len(task.gold_node_ids),
                            "n_hidden_nodes": len(hidden_ids),
                            "any_gold_hidden": hidden,
                            "gold_hidden_fraction": hidden_frac,
                        }

                        t0 = time.perf_counter()
                        bm25_ranking = bm25_rank(corrupted, task.query_text, index=bm25_index)
                        bm25_elapsed = time.perf_counter() - t0
                        rows.append(
                            {
                                **common,
                                "method": "bm25",
                                "runtime_seconds": bm25_elapsed,
                                **_score_row(bm25_ranking, task.gold_node_ids),
                            }
                        )

                        t0 = time.perf_counter()
                        hybrid_ranking = fixed_hybrid_rank(corrupted, task.query_text, bm25_index=bm25_index)
                        hybrid_elapsed = time.perf_counter() - t0
                        rows.append(
                            {
                                **common,
                                "method": "fixed_hybrid",
                                "runtime_seconds": hybrid_elapsed,
                                **_score_row(hybrid_ranking, task.gold_node_ids),
                            }
                        )

                        t0 = time.perf_counter()
                        gated_ranking, policy, diag = gate.rank(
                            corrupted, task.query_text, reference_node_count, bm25_index=bm25_index
                        )
                        gate_elapsed = time.perf_counter() - t0
                        rows.append(
                            {
                                **common,
                                "method": "diagnostic_gate",
                                "runtime_seconds": gate_elapsed,
                                "policy_chosen": policy,
                                "node_coverage": diag.node_coverage,
                                "anchor_confidence": diag.anchor_confidence,
                                "isolated_node_rate": diag.isolated_node_rate,
                                **_score_row(gated_ranking, task.gold_node_ids),
                            }
                        )

    # Enforce, not just assert in prose, that this experiment never touches
    # a Phase-2/Phase-3 dev task: the two id sets collected while iterating
    # must be disjoint, and every scored task id must be an eval-task id.
    assert eval_task_ids.isdisjoint(dev_task_ids), (
        "A task id appears in both the eval and dev splits - split logic diverged "
        "from Phase 2/3's is_dev_split; refusing to proceed."
    )
    scored_task_ids = {r["task_id"] for r in rows}
    assert scored_task_ids.isdisjoint(dev_task_ids), (
        "This experiment scored a dev-split task id, which the playbook forbids "
        "(no threshold tuning / accuracy scoring on held-out dev examples outside "
        "an explicitly-labelled dev-only experiment)."
    )
    assert scored_task_ids == eval_task_ids, "Scored task ids do not match the eval-split task ids."

    # ---- Gold-hidden-aware reporting: accuracy over the gold-visible
    # subset per (method, severity), plus the gold-hidden exclusion counts
    # reported separately rather than silently dropped.
    gold_hidden_by_severity: dict[float, dict] = {}
    for severity in SEVERITIES:
        combos_at_sev = [g for g in gold_hidden_rows if g["severity"] == severity]
        n_total = len(combos_at_sev)
        n_hidden = sum(1 for g in combos_at_sev if g["any_gold_hidden"])
        by_repo_hidden: dict[str, int] = {}
        by_repo_total: dict[str, int] = {}
        for g in combos_at_sev:
            by_repo_total[g["repo"]] = by_repo_total.get(g["repo"], 0) + 1
            if g["any_gold_hidden"]:
                by_repo_hidden[g["repo"]] = by_repo_hidden.get(g["repo"], 0) + 1
        gold_hidden_by_severity[severity] = {
            "n_total_task_seed_combos": n_total,
            "n_gold_hidden": n_hidden,
            "fraction_gold_hidden": (n_hidden / n_total) if n_total else 0.0,
            "n_gold_hidden_by_repo": by_repo_hidden,
            "n_total_by_repo": by_repo_total,
        }

    summary: dict[str, dict] = {}
    for method in METHODS:
        for severity in SEVERITIES:
            visible_rows = [
                r
                for r in rows
                if r["method"] == method and r["severity"] == severity and not r["any_gold_hidden"]
            ]
            hidden_rows = [
                r
                for r in rows
                if r["method"] == method and r["severity"] == severity and r["any_gold_hidden"]
            ]
            key = f"{method}@severity={severity}"
            metrics_block: dict[str, dict] = {}
            for metric_name in METRIC_NAMES:
                by_repo: dict[str, list[float]] = {}
                for r in visible_rows:
                    by_repo.setdefault(r["repo"], []).append(r[metric_name])
                if not by_repo:
                    metrics_block[metric_name] = None
                    continue
                ci = bootstrap_ci_clustered(by_repo, n_resamples=config["bootstrap_resamples"], seed=0)
                metrics_block[metric_name] = {
                    "mean": ci.point_estimate,
                    "ci_low": ci.low,
                    "ci_high": ci.high,
                    "n_observations": sum(len(v) for v in by_repo.values()),
                    "n_repos": len(by_repo),
                }
            summary[key] = {
                "metrics": metrics_block,
                "n_gold_visible_rows": len(visible_rows),
                "n_gold_hidden_rows_excluded": len(hidden_rows),
            }

    peak_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "rows": rows,
        "gold_hidden_rows": gold_hidden_rows,
        "gold_hidden_by_severity": gold_hidden_by_severity,
        "summary": summary,
        "graph_reports": graph_reports,
        "gold_reports": gold_reports,
        "n_eval_tasks_scored": len(eval_task_ids),
        "n_dev_tasks_not_touched": len(dev_task_ids),
        "n_excluded_tasks": excluded_total,
        "dataset_sha256": dataset_sha256,
        "config": config,
        "peak_rss_kb": peak_rss_kb,
        "gate_thresholds": {
            "coverage_floor": gate.coverage_floor,
            "isolated_ceiling": gate.isolated_ceiling,
            "anchor_floor": gate.anchor_floor,
        },
    }


if __name__ == "__main__":
    # Optional CLI overrides — see the matching comment in run_real_pilot.py.
    config_rel = sys.argv[1] if len(sys.argv) > 1 else "configs/pilot_a.yaml"
    output_rel = sys.argv[2] if len(sys.argv) > 2 else "results/coverage_floor_eval"
    output_dir = ROOT / output_rel
    output_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    result = run(ROOT / config_rel)
    total_wall_seconds = time.perf_counter() - t_start

    fieldnames = sorted({k for row in result["rows"] for k in row})
    with (output_dir / "metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result["rows"])

    gold_hidden_fieldnames = sorted({k for row in result["gold_hidden_rows"] for k in row})
    with (output_dir / "gold_hidden_rows.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=gold_hidden_fieldnames)
        writer.writeheader()
        writer.writerows(result["gold_hidden_rows"])

    (output_dir / "summary.json").write_text(json.dumps(result["summary"], indent=2))
    (output_dir / "gold_hidden_by_severity.json").write_text(
        json.dumps(result["gold_hidden_by_severity"], indent=2)
    )
    (output_dir / "graph_reports.json").write_text(json.dumps(result["graph_reports"], indent=2))
    (output_dir / "gold_resolution_reports.json").write_text(json.dumps(result["gold_reports"], indent=2))
    (output_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "dataset_sha256": result["dataset_sha256"],
                "config": result["config"],
                "gate_thresholds": result["gate_thresholds"],
                "n_eval_tasks_scored": result["n_eval_tasks_scored"],
                "n_dev_tasks_not_touched": result["n_dev_tasks_not_touched"],
                "n_excluded_tasks": result["n_excluded_tasks"],
                "total_wall_seconds": total_wall_seconds,
                "peak_rss_kb": result["peak_rss_kb"],
                "n_raw_rows": len(result["rows"]),
            },
            indent=2,
        )
    )
    print(
        f"Coverage-floor eval-split experiment complete: {result['n_eval_tasks_scored']} eval tasks "
        f"scored, {result['n_dev_tasks_not_touched']} dev tasks NOT touched (enforced by assertion), "
        f"{result['n_excluded_tasks']} excluded (gold unresolved, from Phase 2's resolution logic "
        f"re-run here). Wrote {len(result['rows'])} rows to {output_dir}."
    )
    print(f"Wall time: {total_wall_seconds:.1f}s, peak RSS: {result['peak_rss_kb'] / 1024:.0f} MiB")
