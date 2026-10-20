"""Candidate-A real-data pilot: GraphFaultBench on real Loc-Bench V1 issues
against real, statically-built repository call/import graphs.

This is the 21-October decision-gate pilot run referenced throughout
`STATUS.md` / `research/decision_log.md`. It is intentionally scoped (3
repos, ~40+ evaluable issues, 3 seeds, 3 corruption operators x 3 non-zero
severities + a zero-severity healthy control, 5 retrieval baselines) rather
than exhaustive — the goal is a real, reproducible signal to decide on, not
a final paper-grade sweep.

What this script does NOT do (see research/limitations.md for the full list):
- It does not use the organiser's Kaggle graph/embedding bundle (directive
  §6 — avoid the ~23GB download; graphs are built here via static analysis
  instead).
- It does not tune DiagnosticGate thresholds on the dev split it creates;
  the dev split exists for future use and is reported but unused here.
- It does not pass hints_text or patch content to any retriever (leakage
  control, directive §4.1).

Usage: `python experiments/pilot_a/run_real_pilot.py`
"""

from __future__ import annotations

import csv
import hashlib
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
from gemma_research.evidence.perturb import high_centrality_edges, missing_edges, stale_symbol_refs
from gemma_research.evidence.retrieve import (
    BM25Index,
    DiagnosticGate,
    bm25_rank,
    fixed_hybrid_rank,
    graph_expansion_rank,
    repomap_rank,
)
from gemma_research.metrics.scoring import bootstrap_ci_clustered, hit_at_k, reciprocal_rank, strict_acc_at_k

ROOT = Path(__file__).resolve().parents[2]

CORRUPTION_OPS = {
    "missing_edges": missing_edges,
    "high_centrality_edges": high_centrality_edges,
    "stale_symbol_refs": stale_symbol_refs,
}

METHODS = {
    "bm25": lambda g, q, idx: bm25_rank(g, q, index=idx),
    "graph_expansion": lambda g, q, idx: graph_expansion_rank(g, q, bm25_index=idx),
    "fixed_hybrid": lambda g, q, idx: fixed_hybrid_rank(g, q, bm25_index=idx),
    "repomap": lambda g, q, idx: repomap_rank(g, q, bm25_index=idx),
}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _corruption_combos(config: dict) -> list[tuple[str, float]]:
    combos = [("healthy_control", 0.0)]
    for op_name in config["corruption_operators"]:
        for sev in config["severities"]:
            if sev > 0.0:
                combos.append((op_name, sev))
    return combos


def run(config_path: Path) -> dict:
    config = yaml.safe_load(config_path.read_text())
    parquet_path = ROOT / config["loc_bench_parquet"]
    dataset_sha256 = _file_sha256(parquet_path)

    df = load_loc_bench(str(parquet_path), tuple(config["repos"]))
    combos = _corruption_combos(config)
    gate = DiagnosticGate()

    rows: list[dict] = []
    graph_reports = []
    gold_reports = []
    dev_task_ids: list[str] = []
    excluded_total = 0

    for repo in config["repos"]:
        repo_rows = df[df["repo"] == repo]
        for commit, commit_rows in repo_rows.groupby("base_commit"):
            source_root = fetch_repo_snapshot(repo, commit)
            graph, build_report = build_graph_from_source(repo, commit, source_root)
            graph_reports.append(build_report.__dict__)
            # Built once per commit and reused for every task/seed/severity below:
            # none of this pilot's corruption operators change the node set, only
            # edges, so the lexical index (which depends only on node text) is
            # identical throughout — this is a performance cache, not a shortcut
            # that changes any reported score.
            bm25_index = BM25Index(graph.nodes)

            tasks, gold_report = build_tasks_for_commit(commit_rows, graph, repo, commit)
            gold_reports.append(gold_report.__dict__)
            excluded_total += gold_report.n_excluded

            eval_tasks: list[LocalizationTask] = []
            for task in tasks:
                if is_dev_split(task.task_id, config["dev_fraction"]):
                    dev_task_ids.append(task.task_id)
                else:
                    eval_tasks.append(task)

            reference_node_count = len(graph.nodes)
            for task in eval_tasks:
                for seed in config["seeds"]:
                    for operator_name, severity in combos:
                        if operator_name == "healthy_control":
                            corrupted: CodeGraph = graph
                        else:
                            corrupted, _manifest = CORRUPTION_OPS[operator_name](graph, severity, seed)

                        for method_name, method_fn in METHODS.items():
                            t0 = time.perf_counter()
                            ranking = method_fn(corrupted, task.query_text, bm25_index)
                            elapsed = time.perf_counter() - t0
                            rows.append(
                                {
                                    "repo": repo,
                                    "commit": commit,
                                    "task_id": task.task_id,
                                    "method": method_name,
                                    "operator": operator_name,
                                    "severity": severity,
                                    "seed": seed,
                                    "hit_at_1": hit_at_k(ranking, task.gold_node_ids, 1),
                                    "hit_at_3": hit_at_k(ranking, task.gold_node_ids, 3),
                                    "hit_at_5": hit_at_k(ranking, task.gold_node_ids, 5),
                                    "strict_acc_at_5": strict_acc_at_k(ranking, task.gold_node_ids, 5),
                                    "mrr": reciprocal_rank(ranking, task.gold_node_ids),
                                    "runtime_seconds": elapsed,
                                    "n_graph_nodes": len(corrupted.nodes),
                                    "n_graph_edges": len(corrupted.edges),
                                }
                            )

                        t0 = time.perf_counter()
                        gated_ranking, policy, diag = gate.rank(
                            corrupted, task.query_text, reference_node_count, bm25_index=bm25_index
                        )
                        elapsed = time.perf_counter() - t0
                        rows.append(
                            {
                                "repo": repo,
                                "commit": commit,
                                "task_id": task.task_id,
                                "method": "diagnostic_gate",
                                "operator": operator_name,
                                "severity": severity,
                                "seed": seed,
                                "hit_at_1": hit_at_k(gated_ranking, task.gold_node_ids, 1),
                                "hit_at_3": hit_at_k(gated_ranking, task.gold_node_ids, 3),
                                "hit_at_5": hit_at_k(gated_ranking, task.gold_node_ids, 5),
                                "strict_acc_at_5": strict_acc_at_k(gated_ranking, task.gold_node_ids, 5),
                                "mrr": reciprocal_rank(gated_ranking, task.gold_node_ids),
                                "runtime_seconds": elapsed,
                                "n_graph_nodes": len(corrupted.nodes),
                                "n_graph_edges": len(corrupted.edges),
                                "policy_chosen": policy,
                                "node_coverage": diag.node_coverage,
                                "anchor_confidence": diag.anchor_confidence,
                                "isolated_node_rate": diag.isolated_node_rate,
                            }
                        )

    primary_metric = config["primary_metric"]
    summary: dict[str, dict] = {}
    for method in list(METHODS) + ["diagnostic_gate"]:
        for operator_name, severity in combos:
            key = f"{method}@{operator_name}@severity={severity}"
            by_repo: dict[str, list[float]] = {}
            for r in rows:
                if r["method"] == method and r["operator"] == operator_name and r["severity"] == severity:
                    by_repo.setdefault(r["repo"], []).append(r[primary_metric])
            if not by_repo:
                continue
            ci = bootstrap_ci_clustered(by_repo, n_resamples=config["bootstrap_resamples"], seed=0)
            summary[key] = {
                "mean": ci.point_estimate,
                "ci_low": ci.low,
                "ci_high": ci.high,
                "n_observations": sum(len(v) for v in by_repo.values()),
                "n_repos": len(by_repo),
            }

    peak_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "rows": rows,
        "summary": summary,
        "graph_reports": graph_reports,
        "gold_reports": gold_reports,
        "n_eval_tasks": len({r["task_id"] for r in rows}),
        "n_dev_tasks": len(set(dev_task_ids)),
        "n_excluded_tasks": excluded_total,
        "dataset_sha256": dataset_sha256,
        "config": config,
        "peak_rss_kb": peak_rss_kb,
    }


if __name__ == "__main__":
    # Optional CLI overrides, used to split this pilot's repo set across two
    # machines running in parallel (see research/decision_log.md's repo-
    # widening entry) and merge the raw rows afterwards; with no arguments
    # this is identical to the original single-machine, single-config run.
    config_rel = sys.argv[1] if len(sys.argv) > 1 else "configs/pilot_a.yaml"
    output_rel = sys.argv[2] if len(sys.argv) > 2 else "results/pilot"
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

    (output_dir / "summary.json").write_text(json.dumps(result["summary"], indent=2))
    (output_dir / "graph_reports.json").write_text(json.dumps(result["graph_reports"], indent=2))
    (output_dir / "gold_resolution_reports.json").write_text(json.dumps(result["gold_reports"], indent=2))
    (output_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "dataset_sha256": result["dataset_sha256"],
                "config": result["config"],
                "n_eval_tasks": result["n_eval_tasks"],
                "n_dev_tasks": result["n_dev_tasks"],
                "n_excluded_tasks": result["n_excluded_tasks"],
                "total_wall_seconds": total_wall_seconds,
                "peak_rss_kb": result["peak_rss_kb"],
                "n_raw_rows": len(result["rows"]),
            },
            indent=2,
        )
    )
    print(f"Real pilot complete: {result['n_eval_tasks']} eval tasks, "
          f"{result['n_dev_tasks']} dev tasks (unused), {result['n_excluded_tasks']} excluded "
          f"(gold unresolved). Wrote {len(result['rows'])} rows to {output_dir}.")
    print(f"Wall time: {total_wall_seconds:.1f}s, peak RSS: {result['peak_rss_kb'] / 1024:.0f} MiB")
