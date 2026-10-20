"""Phase 3 scoped experiment: the `node_omission` corruption operator,
scored only against the dev split, to inform (not blindly apply) a
recommendation about `DiagnosticGate`'s `isolated_ceiling` threshold.

Background (see `research/novelty_assessment.md` §2-3 and
`research/go_no_go.md` §4 item 2): the Phase 2 pilot
(`experiments/pilot_a/run_real_pilot.py`) used three edge-only corruption
operators. Two of `DiagnosticGate`'s three diagnostic signals
(`node_coverage`, `anchor_confidence`) are structurally insensitive to
edge-only corruption, and the third (`isolated_node_rate`) never crossed
the gate's `isolated_ceiling = 0.5` threshold in that pilot. `node_omission`
(`src/gemma_research/evidence/perturb.py`) already existed in this codebase
with unit tests, but was never wired into a pilot run on real data. This
script is that run.

Critical constraint, enforced in code (not just asserted in prose): this
script scores `node_omission` ONLY against the dev-split tasks that
`is_dev_split(...)` set aside in Phase 2 (and are reported, unused, in
`reports/pilot_results.md` §2). It never touches the 40 eval tasks Phase 2
used for its reported results, per the playbook's prohibition on tuning
diagnostic thresholds on evaluation examples. The eval-task ids are
collected as this script runs and asserted disjoint from the dev-task ids,
and the eval-task count is logged so the constraint is visible, not only
implied.

What this script does NOT do:
- It does not re-run or modify anything in `results/pilot/` (Phase 2's
  frozen eval-set outputs). Its own output goes to
  `results/node_omission_dev/`.
- It does not change `DiagnosticGate`'s thresholds. It only measures the
  signals `compute_diagnostics` already produces, by calling that function
  directly (never reimplementing the `node_coverage` / `isolated_node_rate`
  formulas), so there is no risk of drift between what is analysed here and
  what the gate actually computes at runtime.
- It does not score any retrieval method (`bm25`, `fixed_hybrid`, etc.) —
  this experiment is about the diagnostic signals themselves, not
  retrieval accuracy.

Usage: `python experiments/pilot_a/run_node_omission_experiment.py`
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
from gemma_research.evidence.gold_visibility import any_gold_hidden, gold_hidden_fraction
from gemma_research.evidence.perturb import node_omission
from gemma_research.evidence.retrieve import compute_diagnostics

ROOT = Path(__file__).resolve().parents[2]

# Same severities as configs/pilot_a.yaml. 0.0 is the healthy (uncorrupted)
# control, reusing the convention from run_real_pilot.py's `_corruption_combos`.
SEVERITIES = [0.0, 0.25, 0.5, 0.75]


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def run(config_path: Path) -> dict:
    config = yaml.safe_load(config_path.read_text())
    parquet_path = ROOT / config["loc_bench_parquet"]
    dataset_sha256 = _file_sha256(parquet_path)

    df = load_loc_bench(str(parquet_path), tuple(config["repos"]))

    rows: list[dict] = []
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

            dev_tasks: list[LocalizationTask] = []
            for task in tasks:
                if is_dev_split(task.task_id, config["dev_fraction"]):
                    dev_tasks.append(task)
                    dev_task_ids.add(task.task_id)
                else:
                    # Phase 2's eval task: tracked for the disjointness
                    # check below, never scored here.
                    eval_task_ids.add(task.task_id)

            reference_node_count = len(graph.nodes)
            for task in dev_tasks:
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

                        # Deliberately no cached bm25_index here: unlike Phase 2's
                        # edge-only operators, node_omission changes the node set,
                        # so compute_diagnostics must build its index from the
                        # *current* (possibly-reduced) node set to match what
                        # DiagnosticGate would actually see at runtime. Passing a
                        # stale full-graph index would let a hidden node's text
                        # still contribute to anchor_confidence.
                        diag = compute_diagnostics(
                            corrupted, task.query_text, reference_node_count=reference_node_count
                        )

                        rows.append(
                            {
                                "repo": repo,
                                "commit": commit,
                                "task_id": task.task_id,
                                "operator": operator_name,
                                "severity": severity,
                                "seed": seed,
                                "node_coverage": diag.node_coverage,
                                "anchor_confidence": diag.anchor_confidence,
                                "isolated_node_rate": diag.isolated_node_rate,
                                "reference_node_count": reference_node_count,
                                "n_graph_nodes": len(corrupted.nodes),
                                "n_hidden_nodes": len(hidden_ids),
                                "n_gold_ids": len(task.gold_node_ids),
                                "any_gold_hidden": any_gold_hidden(task.gold_node_ids, hidden_ids),
                                "gold_hidden_fraction": gold_hidden_fraction(
                                    task.gold_node_ids, hidden_ids
                                ),
                            }
                        )

    # Enforce, not just assert in prose, that this experiment never touches
    # a Phase-2 eval task: the two id sets collected while iterating must be
    # disjoint, and only dev_task_ids may appear in `rows`.
    assert eval_task_ids.isdisjoint(dev_task_ids), (
        "A task id appears in both the eval and dev splits - split logic diverged "
        "from Phase 2's is_dev_split; refusing to proceed."
    )
    scored_task_ids = {r["task_id"] for r in rows}
    assert scored_task_ids.isdisjoint(eval_task_ids), (
        "This experiment scored a Phase-2 eval task id, which the playbook "
        "forbids (no threshold tuning on evaluation examples)."
    )
    assert scored_task_ids == dev_task_ids, "Scored task ids do not match the dev-split task ids."

    peak_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "rows": rows,
        "graph_reports": graph_reports,
        "gold_reports": gold_reports,
        "n_dev_tasks_scored": len(dev_task_ids),
        "n_eval_tasks_not_touched": len(eval_task_ids),
        "n_excluded_tasks": excluded_total,
        "dataset_sha256": dataset_sha256,
        "config": config,
        "peak_rss_kb": peak_rss_kb,
    }


if __name__ == "__main__":
    # Optional CLI overrides — see the matching comment in run_real_pilot.py.
    config_rel = sys.argv[1] if len(sys.argv) > 1 else "configs/pilot_a.yaml"
    output_rel = sys.argv[2] if len(sys.argv) > 2 else "results/node_omission_dev"
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

    (output_dir / "graph_reports.json").write_text(json.dumps(result["graph_reports"], indent=2))
    (output_dir / "gold_resolution_reports.json").write_text(json.dumps(result["gold_reports"], indent=2))
    (output_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "dataset_sha256": result["dataset_sha256"],
                "config": result["config"],
                "n_dev_tasks_scored": result["n_dev_tasks_scored"],
                "n_eval_tasks_not_touched": result["n_eval_tasks_not_touched"],
                "n_excluded_tasks": result["n_excluded_tasks"],
                "total_wall_seconds": total_wall_seconds,
                "peak_rss_kb": result["peak_rss_kb"],
                "n_raw_rows": len(result["rows"]),
            },
            indent=2,
        )
    )
    print(
        f"Node-omission dev-split experiment complete: {result['n_dev_tasks_scored']} dev tasks "
        f"scored, {result['n_eval_tasks_not_touched']} Phase-2 eval tasks NOT touched (enforced by "
        f"assertion), {result['n_excluded_tasks']} excluded (gold unresolved, from Phase 2's "
        "resolution logic re-run here). "
        f"Wrote {len(result['rows'])} rows to {output_dir}."
    )
    print(f"Wall time: {total_wall_seconds:.1f}s, peak RSS: {result['peak_rss_kb'] / 1024:.0f} MiB")
