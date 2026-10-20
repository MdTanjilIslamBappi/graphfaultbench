"""Merges the two-machine repo-widening split (research/decision_log.md's
repo-widening entry) back into the canonical Phase 2/3/4 result
directories.

`configs/pilot_a.yaml` lists all six repos (the original python/mypy,
dask/dask, PrefectHQ/prefect plus the widening's numpy/numpy, scipy/scipy,
aio-libs/aiohttp), but the pilot itself was run as two independent
processes against the split configs `pilot_a_set1.yaml` (first three
repos, run locally) and `pilot_a_set2.yaml` (last three, run on a second
machine) so they could execute in parallel. Each phase (run_real_pilot.py,
run_node_omission_experiment.py, run_coverage_floor_eval.py) therefore has
two raw output directories (`results/<phase>_set1/`, `results/<phase>_set2/`)
that this script concatenates into the single canonical directory
(`results/<phase>/`) the manuscript and writeup actually cite.

This is a pure merge of already-computed raw rows -- it does not re-run
any retrieval method, corruption operator, or graph build. For the two
phases that publish a `summary.json` (pilot, coverage_floor_eval), the
bootstrap confidence intervals ARE recomputed here, over the combined
six-repo `by_repo` grouping, using the exact same grouping keys and
`bootstrap_ci_clustered` call as the original scripts -- this is
mathematically equivalent to having run the un-split six-repo config
directly, because `bootstrap_ci_clustered` clusters by repo and the two
splits' repo sets are disjoint. `node_omission_dev` has no summary.json
in either split (Phase 3 never computed one) and gets none here either.

What this script does NOT do:
- It does not touch the `_set1`/`_set2` directories themselves (left
  alone as the committed provenance for each half's raw run).
- It does not change any config, threshold, or scoring formula.
- It does not silently paper over a mismatch: the two splits' dataset
  sha256 values and non-`repos` config fields must agree, or the merge
  refuses to run.

Usage: `python experiments/pilot_a/merge_repo_widening.py`
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from gemma_research.metrics.scoring import bootstrap_ci_clustered

ROOT = Path(__file__).resolve().parents[2]

# (phase directory name, has a gold_hidden_rows.csv, has a summary.json)
PHASES = [
    ("pilot", False, True),
    ("node_omission_dev", False, False),
    ("coverage_floor_eval", True, True),
]

PILOT_METHODS = ("bm25", "graph_expansion", "fixed_hybrid", "repomap", "diagnostic_gate")
COVERAGE_METHODS = ("bm25", "fixed_hybrid", "diagnostic_gate")
COVERAGE_SEVERITIES = [0.0, 0.25, 0.5, 0.75]
METRIC_NAMES = ("hit_at_1", "hit_at_3", "hit_at_5", "strict_acc_at_5", "mrr")


def _load_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _write_csv_rows(path: Path, rows: list[dict]) -> None:
    fieldnames = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _assert_manifests_consistent(manifest1: dict, manifest2: dict) -> None:
    assert manifest1["dataset_sha256"] == manifest2["dataset_sha256"], (
        "set1 and set2 scored different loc_bench_v1_test.parquet files "
        f"({manifest1['dataset_sha256']} vs {manifest2['dataset_sha256']}) "
        "-- refusing to merge results that are not provably from the same dataset."
    )
    for key in ("seeds", "severities", "corruption_operators", "k_values", "primary_metric",
                "dev_fraction", "bootstrap_resamples", "alpha", "loc_bench_parquet"):
        v1, v2 = manifest1["config"][key], manifest2["config"][key]
        assert v1 == v2, f"set1/set2 config field {key!r} differs ({v1!r} vs {v2!r}) -- refusing to merge."
    assert set(manifest1["config"]["repos"]).isdisjoint(manifest2["config"]["repos"]), (
        "set1 and set2 repo lists overlap -- merging would double-count a repo's rows."
    )


def _merge_pilot_summary(rows: list[dict], config: dict) -> dict:
    combos = {(r["operator"], float(r["severity"])) for r in rows}
    summary: dict[str, dict] = {}
    for method in PILOT_METHODS:
        for operator_name, severity in combos:
            key = f"{method}@{operator_name}@severity={severity}"
            by_repo: dict[str, list[float]] = {}
            for r in rows:
                if r["method"] == method and r["operator"] == operator_name and float(r["severity"]) == severity:
                    by_repo.setdefault(r["repo"], []).append(float(r[config["primary_metric"]]))
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
    return summary


def _merge_coverage_floor_eval_summary(rows: list[dict], config: dict) -> dict:
    summary: dict[str, dict] = {}
    for method in COVERAGE_METHODS:
        for severity in COVERAGE_SEVERITIES:
            visible_rows = [
                r for r in rows
                if r["method"] == method and float(r["severity"]) == severity
                and r["any_gold_hidden"] in ("False", False)
            ]
            hidden_rows = [
                r for r in rows
                if r["method"] == method and float(r["severity"]) == severity
                and r["any_gold_hidden"] in ("True", True)
            ]
            key = f"{method}@severity={severity}"
            metrics_block: dict[str, dict | None] = {}
            for metric_name in METRIC_NAMES:
                by_repo: dict[str, list[float]] = {}
                for r in visible_rows:
                    by_repo.setdefault(r["repo"], []).append(float(r[metric_name]))
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
    return summary


def _merge_gold_hidden_by_severity(gold_hidden_rows: list[dict]) -> dict:
    severities = sorted({float(r["severity"]) for r in gold_hidden_rows})
    out: dict[float, dict] = {}
    for severity in severities:
        combos_at_sev = [g for g in gold_hidden_rows if float(g["severity"]) == severity]
        n_total = len(combos_at_sev)
        n_hidden = sum(1 for g in combos_at_sev if g["any_gold_hidden"] in ("True", True))
        by_repo_hidden: dict[str, int] = {}
        by_repo_total: dict[str, int] = {}
        for g in combos_at_sev:
            by_repo_total[g["repo"]] = by_repo_total.get(g["repo"], 0) + 1
            if g["any_gold_hidden"] in ("True", True):
                by_repo_hidden[g["repo"]] = by_repo_hidden.get(g["repo"], 0) + 1
        out[severity] = {
            "n_total_task_seed_combos": n_total,
            "n_gold_hidden": n_hidden,
            "fraction_gold_hidden": (n_hidden / n_total) if n_total else 0.0,
            "n_gold_hidden_by_repo": by_repo_hidden,
            "n_total_by_repo": by_repo_total,
        }
    return out


def merge_phase(phase: str, has_gold_hidden: bool, has_summary: bool, merged_config: dict) -> dict:
    dir1 = ROOT / "results" / f"{phase}_set1"
    dir2 = ROOT / "results" / f"{phase}_set2"
    out_dir = ROOT / "results" / phase
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest1 = json.loads((dir1 / "run_manifest.json").read_text())
    manifest2 = json.loads((dir2 / "run_manifest.json").read_text())
    _assert_manifests_consistent(manifest1, manifest2)

    rows = _load_csv_rows(dir1 / "metrics.csv") + _load_csv_rows(dir2 / "metrics.csv")
    task_ids_1 = {r["task_id"] for r in _load_csv_rows(dir1 / "metrics.csv")}
    task_ids_2 = {r["task_id"] for r in _load_csv_rows(dir2 / "metrics.csv")}
    assert task_ids_1.isdisjoint(task_ids_2), (
        f"{phase}: set1 and set2 share a task_id -- refusing to merge (would double-count a task)."
    )
    _write_csv_rows(out_dir / "metrics.csv", rows)

    graph_reports = json.loads((dir1 / "graph_reports.json").read_text()) + json.loads(
        (dir2 / "graph_reports.json").read_text()
    )
    (out_dir / "graph_reports.json").write_text(json.dumps(graph_reports, indent=2))

    gold_reports = json.loads((dir1 / "gold_resolution_reports.json").read_text()) + json.loads(
        (dir2 / "gold_resolution_reports.json").read_text()
    )
    (out_dir / "gold_resolution_reports.json").write_text(json.dumps(gold_reports, indent=2))

    gold_hidden_rows: list[dict] = []
    if has_gold_hidden:
        gold_hidden_rows = _load_csv_rows(dir1 / "gold_hidden_rows.csv") + _load_csv_rows(
            dir2 / "gold_hidden_rows.csv"
        )
        _write_csv_rows(out_dir / "gold_hidden_rows.csv", gold_hidden_rows)
        gold_hidden_by_severity = _merge_gold_hidden_by_severity(gold_hidden_rows)
        (out_dir / "gold_hidden_by_severity.json").write_text(json.dumps(gold_hidden_by_severity, indent=2))

    summary: dict = {}
    if has_summary:
        if phase == "pilot":
            summary = _merge_pilot_summary(rows, merged_config)
        elif phase == "coverage_floor_eval":
            summary = _merge_coverage_floor_eval_summary(rows, merged_config)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    n_excluded_total = manifest1["n_excluded_tasks"] + manifest2["n_excluded_tasks"]
    merged_manifest = {
        "dataset_sha256": manifest1["dataset_sha256"],
        "config": merged_config,
        "n_excluded_tasks": n_excluded_total,
        "total_wall_seconds_set1": manifest1["total_wall_seconds"],
        "total_wall_seconds_set2": manifest2["total_wall_seconds"],
        "peak_rss_kb": max(manifest1["peak_rss_kb"], manifest2["peak_rss_kb"]),
        "n_raw_rows": len(rows),
        "merged_from": [f"results/{phase}_set1", f"results/{phase}_set2"],
    }
    for key in ("gate_thresholds",):
        if key in manifest1:
            merged_manifest[key] = manifest1[key]
    if phase == "pilot":
        merged_manifest["n_eval_tasks"] = manifest1["n_eval_tasks"] + manifest2["n_eval_tasks"]
        merged_manifest["n_dev_tasks"] = manifest1["n_dev_tasks"] + manifest2["n_dev_tasks"]
    else:
        key_scored = "n_dev_tasks_scored" if phase == "node_omission_dev" else "n_eval_tasks_scored"
        key_untouched = "n_eval_tasks_not_touched" if phase == "node_omission_dev" else "n_dev_tasks_not_touched"
        merged_manifest[key_scored] = manifest1[key_scored] + manifest2[key_scored]
        merged_manifest[key_untouched] = manifest1[key_untouched] + manifest2[key_untouched]
    (out_dir / "run_manifest.json").write_text(json.dumps(merged_manifest, indent=2))

    return {
        "phase": phase,
        "n_raw_rows": len(rows),
        "n_excluded_tasks": n_excluded_total,
        "out_dir": str(out_dir),
    }


if __name__ == "__main__":
    merged_config = yaml.safe_load((ROOT / "configs" / "pilot_a.yaml").read_text())
    assert len(merged_config["repos"]) == 6, (
        f"configs/pilot_a.yaml lists {len(merged_config['repos'])} repos, expected 6 -- "
        "re-check before merging against a config that no longer matches set1+set2."
    )
    results = []
    for phase, has_gold_hidden, has_summary in PHASES:
        results.append(merge_phase(phase, has_gold_hidden, has_summary, merged_config))
    for r in results:
        print(
            f"Merged {r['phase']}: {r['n_raw_rows']} raw rows, {r['n_excluded_tasks']} excluded "
            f"tasks total -> {r['out_dir']}"
        )
