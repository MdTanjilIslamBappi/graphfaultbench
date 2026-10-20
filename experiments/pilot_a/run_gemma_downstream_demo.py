"""Optional Gemma 4 downstream demonstration (secondary evidence).

Per `Gemma4_Research_Contingency_v2.md` protocol step 7 and
`Gemma4_Paper_Track_Competition_Playbook.md`'s "one small, properly
controlled Gemma 4 downstream demonstration... label that as secondary
evidence and report full generation parameters" — this is deliberately
small and separate from the Phase 2-4 pilots, not a replacement for them.

Design, stated explicitly for reproducibility (see
`research/gemma4_downstream_go_no_go.md` for the full feasibility/go-no-go
trail):
- Reuses the exact same repos, commits, graphs, and `LocalizationTask`
  definitions as the Phase 2 pilot (`run_real_pilot.py`) via the same
  harness functions, so this demo's own `fixed_hybrid` numbers are directly
  comparable to, but independently recomputed on, the smaller task subset
  used here (not copied from results/pilot/ — paired per-task comparison
  requires scoring both methods on identical rows).
- A fixed, documented, non-cherry-picked stratified sample: 5 eval tasks
  per repo (15 total), chosen by `random.Random(DEMO_SAMPLE_SEED).sample`
  over the sorted eval task-id list — deterministic and reproducible from
  this file alone.
- Two severities only: 0.0 (healthy control) and 0.5 (missing_edges,
  seed=1 — the same operator/seed Phase 2 used), not the full Phase 2-4
  grid. This keeps total local CPU inference time bounded (~30 Gemma calls)
  while still exercising both the uncorrupted and a meaningfully corrupted
  condition.
- Gemma reranks `fixed_hybrid_rank`'s own top-15 candidate pool (see
  `gemma_research.evidence.gemma_rerank` for why), so this measures
  reranking quality within a fixed shortlist, not open-candidate retrieval.

Usage: `uv run python experiments/pilot_a/run_gemma_downstream_demo.py`
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import yaml
from llama_cpp import Llama

from gemma_research.data.graph_builder import build_graph_from_source
from gemma_research.data.loc_bench_tasks import build_tasks_for_commit, is_dev_split, load_loc_bench
from gemma_research.data.repo_source import fetch_repo_snapshot
from gemma_research.data.types import CodeGraph, LocalizationTask
from gemma_research.evidence.gemma_rerank import GENERATION_PARAMS, gemma_rerank
from gemma_research.evidence.perturb import missing_edges
from gemma_research.evidence.retrieve import BM25Index, fixed_hybrid_rank
from gemma_research.metrics.scoring import (
    bootstrap_ci_clustered,
    hit_at_k,
    reciprocal_rank,
    strict_acc_at_k,
)

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = (
    ROOT
    / "manifests/raw_data/gemma4/models/google/gemma-4/gguf/"
    "gemma-4-e2b-it-qat-q4_0-gguf/2/gemma-4-E2B_q4_0-it.gguf"
)
DEMO_SAMPLE_SEED = 20261020  # documented, fixed; see module docstring
TASKS_PER_REPO = 5
POOL_SIZE = 15
CORRUPTION_SEED = 1
SEVERITIES = (0.0, 0.5)


def _select_sample(eval_tasks: list[LocalizationTask]) -> list[LocalizationTask]:
    """Pick `TASKS_PER_REPO` tasks, pooled across every commit a repo
    contributes to Loc-Bench V1 (dask/dask and PrefectHQ/prefect are split
    across 16-19 distinct base_commits, mostly one task each — sampling
    per-commit, as an earlier version of this script did, silently pulled
    nearly every available task instead of a bounded, documented 5)."""
    ordered = sorted(eval_tasks, key=lambda t: t.task_id)
    rng = random.Random(DEMO_SAMPLE_SEED)
    n = min(TASKS_PER_REPO, len(ordered))
    return rng.sample(ordered, n)


def run(config_path: Path) -> dict:
    config = yaml.safe_load(config_path.read_text())
    parquet_path = ROOT / config["loc_bench_parquet"]
    df = load_loc_bench(str(parquet_path), tuple(config["repos"]))

    llm = Llama(model_path=str(MODEL_PATH), n_ctx=4096, n_threads=12, verbose=False)

    rows: list[dict] = []
    raw_outputs: list[dict] = []
    sample_task_ids: dict[str, list[str]] = {}

    for repo in config["repos"]:
        repo_rows = df[df["repo"] == repo]
        # Pass 1: build every commit's graph once (cheap, cached locally) and
        # pool ALL its eval tasks before sampling — a repo here is split
        # across many distinct base_commits (dask/dask: 19, PrefectHQ/prefect:
        # 16, mostly ~1 task each), so sampling per-commit instead of
        # per-repo would silently pull nearly every available task.
        pooled: list[tuple[LocalizationTask, CodeGraph, BM25Index]] = []
        for commit, commit_rows in repo_rows.groupby("base_commit"):
            source_root = fetch_repo_snapshot(repo, commit)
            graph, _ = build_graph_from_source(repo, commit, source_root)
            bm25_index = BM25Index(graph.nodes)
            tasks, _ = build_tasks_for_commit(commit_rows, graph, repo, commit)
            for task in tasks:
                if not is_dev_split(task.task_id, config["dev_fraction"]):
                    pooled.append((task, graph, bm25_index))

        sample = _select_sample([t for t, _, _ in pooled])
        sample_ids = {t.task_id for t in sample}
        sample_task_ids[repo] = sorted(sample_ids)
        selected = [(t, g, idx) for t, g, idx in pooled if t.task_id in sample_ids]

        # Pass 2: run the (expensive) scoring loop only on the sampled subset.
        for task, graph, bm25_index in selected:
            for severity in SEVERITIES:
                corrupted: CodeGraph
                if severity == 0.0:
                    corrupted = graph
                else:
                    corrupted, _ = missing_edges(graph, severity, CORRUPTION_SEED)

                t0 = time.perf_counter()
                fh_ranking = fixed_hybrid_rank(corrupted, task.query_text, bm25_index=bm25_index)
                fh_elapsed = time.perf_counter() - t0
                rows.append(
                    {
                        "repo": repo,
                        "task_id": task.task_id,
                        "severity": severity,
                        "method": "fixed_hybrid",
                        "hit_at_1": hit_at_k(fh_ranking, task.gold_node_ids, 1),
                        "hit_at_3": hit_at_k(fh_ranking, task.gold_node_ids, 3),
                        "hit_at_5": hit_at_k(fh_ranking, task.gold_node_ids, 5),
                        "strict_acc_at_5": strict_acc_at_k(fh_ranking, task.gold_node_ids, 5),
                        "mrr": reciprocal_rank(fh_ranking, task.gold_node_ids),
                        "runtime_seconds": fh_elapsed,
                        "n_parsed_valid": None,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                    }
                )

                result = gemma_rerank(llm, corrupted, task.query_text, pool_size=POOL_SIZE, bm25_index=bm25_index)
                rows.append(
                    {
                        "repo": repo,
                        "task_id": task.task_id,
                        "severity": severity,
                        "method": "gemma_e2b_rerank",
                        "hit_at_1": hit_at_k(result.ranking, task.gold_node_ids, 1),
                        "hit_at_3": hit_at_k(result.ranking, task.gold_node_ids, 3),
                        "hit_at_5": hit_at_k(result.ranking, task.gold_node_ids, 5),
                        "strict_acc_at_5": strict_acc_at_k(result.ranking, task.gold_node_ids, 5),
                        "mrr": reciprocal_rank(result.ranking, task.gold_node_ids),
                        "runtime_seconds": result.runtime_seconds,
                        "n_parsed_valid": result.n_parsed_valid,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                    }
                )
                raw_outputs.append(
                    {
                        "repo": repo,
                        "task_id": task.task_id,
                        "severity": severity,
                        "candidate_pool": list(result.candidate_pool),
                        "raw_output": result.raw_output,
                        "gold_node_ids": sorted(task.gold_node_ids),
                    }
                )
                print(
                    f"  {repo} {task.task_id} sev={severity}: "
                    f"fixed_hybrid hit@5={rows[-2]['hit_at_5']} "
                    f"gemma hit@5={rows[-1]['hit_at_5']} "
                    f"({result.runtime_seconds:.1f}s, {result.n_parsed_valid} parsed)"
                )

    primary_metric = config["primary_metric"]
    summary: dict[str, dict] = {}
    for method in ("fixed_hybrid", "gemma_e2b_rerank"):
        for severity in SEVERITIES:
            by_repo: dict[str, list[float]] = {}
            for r in rows:
                if r["method"] == method and r["severity"] == severity:
                    by_repo.setdefault(r["repo"], []).append(r[primary_metric])
            if not by_repo:
                continue
            ci = bootstrap_ci_clustered(by_repo, n_resamples=config["bootstrap_resamples"], seed=0)
            summary[f"{method}@severity={severity}"] = {
                "mean": ci.point_estimate,
                "ci_low": ci.low,
                "ci_high": ci.high,
                "n_observations": sum(len(v) for v in by_repo.values()),
                "n_repos": len(by_repo),
            }

    return {
        "rows": rows,
        "raw_outputs": raw_outputs,
        "summary": summary,
        "sample_task_ids": sample_task_ids,
        "config": {
            "demo_sample_seed": DEMO_SAMPLE_SEED,
            "tasks_per_repo": TASKS_PER_REPO,
            "pool_size": POOL_SIZE,
            "corruption_seed": CORRUPTION_SEED,
            "severities": list(SEVERITIES),
            "primary_metric": primary_metric,
            "model": "google/gemma-4 E2B, Q4_0 GGUF (QAT), local CPU inference via llama-cpp-python",
            "generation_params": GENERATION_PARAMS,
        },
    }


if __name__ == "__main__":
    output_dir = ROOT / "results" / "gemma_downstream_demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    result = run(ROOT / "configs" / "pilot_a.yaml")
    total_wall_seconds = time.perf_counter() - t_start

    (output_dir / "metrics.json").write_text(json.dumps(result["rows"], indent=2))
    (output_dir / "raw_outputs.json").write_text(json.dumps(result["raw_outputs"], indent=2))
    (output_dir / "summary.json").write_text(json.dumps(result["summary"], indent=2))
    (output_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "config": result["config"],
                "sample_task_ids": result["sample_task_ids"],
                "n_rows": len(result["rows"]),
                "total_wall_seconds": total_wall_seconds,
            },
            indent=2,
        )
    )
    print(f"\nGemma downstream demo complete. {len(result['rows'])} rows written to {output_dir}.")
    print(f"Wall time: {total_wall_seconds:.1f}s")
    print(json.dumps(result["summary"], indent=2))
