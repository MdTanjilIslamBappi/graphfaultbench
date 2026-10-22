"""Bounded `repomap` correction run (approved 2026-10-22; see
the internal correction proposal (withheld from this release)).

Re-runs ONLY `stale_symbol_refs` (severities > 0) for two methods on the same
tasks, seeds and graphs as the original experiments:
  repomap_original   - repomap_rank as it was (dangling ids enter PageRank)
  repomap_corrected  - repomap_rank(exclude_unknown_nodes=True)
and stores the top-10 ranking and the number of dangling ids in the top-5/10,
which the original runs did not keep. Original result directories are not
touched; output goes to a new directory.

Usage: python experiments/pilot_a/run_repomap_correction.py CONFIG OUTDIR
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import yaml

from gemma_research.data.graph_builder import build_graph_from_source
from gemma_research.data.loc_bench_tasks import build_tasks_for_commit, is_dev_split, load_loc_bench
from gemma_research.data.repo_source import fetch_repo_snapshot
from gemma_research.evidence.perturb import stale_symbol_refs
from gemma_research.evidence.retrieve import BM25Index, repomap_rank
from gemma_research.metrics.scoring import hit_at_k, reciprocal_rank

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {
    "repomap_original": lambda g, q, idx: repomap_rank(g, q, bm25_index=idx),
    "repomap_corrected": lambda g, q, idx: repomap_rank(g, q, bm25_index=idx, exclude_unknown_nodes=True),
}


def main(config_rel: str, out_rel: str) -> None:
    config = yaml.safe_load((ROOT / config_rel).read_text())
    out = ROOT / out_rel
    out.mkdir(parents=True, exist_ok=True)
    df = load_loc_bench(str(ROOT / config["loc_bench_parquet"]), tuple(config["repos"]))
    severities = [s for s in config["severities"] if s > 0.0]
    t0 = time.perf_counter()
    n = 0
    with (out / "rankings.jsonl").open("w") as f:
        for repo in config["repos"]:
            for commit, commit_rows in df[df["repo"] == repo].groupby("base_commit"):
                graph, _ = build_graph_from_source(repo, commit, fetch_repo_snapshot(repo, commit))
                idx = BM25Index(graph.nodes)
                tasks, _ = build_tasks_for_commit(commit_rows, graph, repo, commit)
                for task in tasks:
                    if is_dev_split(task.task_id, config["dev_fraction"]):
                        continue
                    for seed in config["seeds"]:
                        for sev in severities:
                            corrupted, _m = stale_symbol_refs(graph, sev, seed)
                            for name, fn in VARIANTS.items():
                                ranking = fn(corrupted, task.query_text, idx)
                                ids = [c.node_id for c in ranking]
                                f.write(
                                    json.dumps(
                                        {
                                            "repo": repo,
                                            "task_id": task.task_id,
                                            "method": name,
                                            "severity": sev,
                                            "seed": seed,
                                            "hit_at_5": hit_at_k(ranking, task.gold_node_ids, 5),
                                            "mrr": reciprocal_rank(ranking, task.gold_node_ids),
                                            "dangling_in_top5": sum(i.startswith("__DANGLING__:") for i in ids[:5]),
                                            "dangling_in_top10": sum(i.startswith("__DANGLING__:") for i in ids[:10]),
                                            "top10": ids[:10],
                                        }
                                    )
                                    + "\n"
                                )
                                n += 1
    (out / "run_manifest.json").write_text(
        json.dumps({"config": config_rel, "n_rows": n, "wall_seconds": time.perf_counter() - t0}, indent=2)
    )
    print(f"wrote {n} rows to {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
