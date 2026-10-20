"""Tests the continuously-weighted gate variant named as future work in
`paper/manuscript.md` section 7 ("a learned or continuously-weighted
combination of the three diagnostic signals, rather than a single
binary-threshold gate"), built in response to the adversarial-challenge
finding in `research/kaggle_judging_simulation.md` section 2 item 4: a
sharp reviewer would ask why the proposed fix was never tried, given time
remained before the deadline.

This is the direct sequel to `run_coverage_floor_eval.py` (Phase 4): same
eval-split tasks, same `node_omission` corruption, same severities/seeds,
same metrics and clustered-bootstrap procedure -- the only addition is a
fourth scored method, `weighted_gate` (`WeightedDiagnosticGate`), so the
binary `diagnostic_gate` and the continuous `weighted_gate` are compared
on identical corrupted graphs, not separately re-measured conditions.

What this script does NOT do:
- It does not touch, re-run, or modify `results/pilot/`, `results/node_omission_dev/`
  or `results/coverage_floor_eval/` -- all three stay frozen. Its own
  output goes to `results/weighted_gate_eval/` (or a CLI-supplied override).
- It does not change `DiagnosticGate`'s thresholds or
  `WeightedDiagnosticGate`'s weight formula. Both are asserted against
  their real, already-fixed default values before anything runs, the
  same discipline `run_coverage_floor_eval.py` applies.
- It does not pre-commit to a result. Whatever the comparison actually
  shows -- `weighted_gate` beating, tying, or losing to `fixed_hybrid`/
  `diagnostic_gate` -- is reported as-is.

Usage: `python experiments/pilot_a/run_weighted_gate_eval.py [config_path] [output_dir]`
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
from gemma_research.evidence.retrieve import (
    BM25Index,
    DiagnosticGate,
    WeightedDiagnosticGate,
    bm25_rank,
    fixed_hybrid_rank,
)
from gemma_research.metrics.scoring import (
    bootstrap_ci_clustered,
    hit_at_k,
    reciprocal_rank,
    strict_acc_at_k,
)

ROOT = Path(__file__).resolve().parents[2]

SEVERITIES = [0.0, 0.25, 0.5, 0.75]

METRIC_NAMES = ("hit_at_1", "hit_at_3", "hit_at_5", "strict_acc_at_5", "mrr")

METHODS = ("bm25", "fixed_hybrid", "diagnostic_gate", "weighted_gate")


def _assert_params_unchanged() -> tuple[DiagnosticGate, WeightedDiagnosticGate]:
    """Same discipline as run_coverage_floor_eval.py's
    `_assert_gate_thresholds_unchanged`, extended to the new gate: read the
    real `__init__` defaults via `inspect`, not a hardcoded copy, and fail
    loudly if either gate's parameters ever drift from what this script
    assumes."""
    sig = inspect.signature(DiagnosticGate.__init__)
    assert sig.parameters["coverage_floor"].default == 0.6
    assert sig.parameters["isolated_ceiling"].default == 0.5
    assert sig.parameters["anchor_floor"].default == 0.1
    gate = DiagnosticGate()
    assert (gate.coverage_floor, gate.isolated_ceiling, gate.anchor_floor) == (0.6, 0.5, 0.1)

    wsig = inspect.signature(WeightedDiagnosticGate.__init__)
    assert wsig.parameters["anchor_floor"].default == 0.1, (
        "WeightedDiagnosticGate's anchor_floor default changed from 0.1 -- "
        "refusing to proceed without re-reading this script's assumptions."
    )
    weighted_gate = WeightedDiagnosticGate()
    assert weighted_gate.anchor_floor == 0.1
    return gate, weighted_gate


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _score_row(ranking, gold_ids: frozenset[str]) -> dict[str, float]:
    return {
        "hit_at_1": hit_at_k(ranking, gold_ids, 1),
        "hit_at_3": hit_at_k(ranking, gold_ids, 3),
        "hit_at_5": hit_at_k(ranking, gold_ids, 5),
        "strict_acc_at_5": strict_acc_at_k(ranking, gold_ids, 5),
        "mrr": reciprocal_rank(ranking, gold_ids),
    }


def run(config_path: Path) -> dict:
    gate, weighted_gate = _assert_params_unchanged()

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

                        t0 = time.perf_counter()
                        weighted_ranking, weight, wdiag = weighted_gate.rank(
                            corrupted, task.query_text, reference_node_count, bm25_index=bm25_index
                        )
                        weighted_elapsed = time.perf_counter() - t0
                        rows.append(
                            {
                                **common,
                                "method": "weighted_gate",
                                "runtime_seconds": weighted_elapsed,
                                "lexical_weight": weight,
                                "node_coverage": wdiag.node_coverage,
                                "anchor_confidence": wdiag.anchor_confidence,
                                "isolated_node_rate": wdiag.isolated_node_rate,
                                **_score_row(weighted_ranking, task.gold_node_ids),
                            }
                        )

    assert eval_task_ids.isdisjoint(dev_task_ids), (
        "A task id appears in both the eval and dev splits - split logic diverged "
        "from Phase 2/3's is_dev_split; refusing to proceed."
    )
    scored_task_ids = {r["task_id"] for r in rows}
    assert scored_task_ids.isdisjoint(dev_task_ids), (
        "This experiment scored a dev-split task id, which the playbook forbids."
    )
    assert scored_task_ids == eval_task_ids, "Scored task ids do not match the eval-split task ids."

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
        "weighted_gate_anchor_floor": weighted_gate.anchor_floor,
    }


if __name__ == "__main__":
    config_rel = sys.argv[1] if len(sys.argv) > 1 else "configs/pilot_a.yaml"
    output_rel = sys.argv[2] if len(sys.argv) > 2 else "results/weighted_gate_eval"
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
                "weighted_gate_anchor_floor": result["weighted_gate_anchor_floor"],
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
        f"Weighted-gate eval-split experiment complete: {result['n_eval_tasks_scored']} eval tasks "
        f"scored, {result['n_dev_tasks_not_touched']} dev tasks NOT touched (enforced by assertion), "
        f"{result['n_excluded_tasks']} excluded. Wrote {len(result['rows'])} rows to {output_dir}."
    )
    print(f"Wall time: {total_wall_seconds:.1f}s, peak RSS: {result['peak_rss_kb'] / 1024:.0f} MiB")
