"""Gemma 4 E2B reranking v2 (numbered, grammar-constrained). See docs/GEMMA_V2_PREREGISTRATION.md.

Resumable: appends one JSON line per (task, severity) to results/gemma_v2/calls.jsonl and skips done pairs.
Usage: uv run python experiments/pilot_a/run_gemma_v2.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import yaml
from llama_cpp import Llama, LlamaGrammar

from gemma_research.data.graph_builder import build_graph_from_source
from gemma_research.data.loc_bench_tasks import build_tasks_for_commit, is_dev_split, load_loc_bench
from gemma_research.data.repo_source import fetch_repo_snapshot
from gemma_research.evidence.gemma_rerank import (
    GENERATION_PARAMS,
    gemma_rerank_indexed,
    indexed_grammar_text,
)
from gemma_research.evidence.perturb import missing_edges
from gemma_research.evidence.retrieve import BM25Index, bm25_rank, fixed_hybrid_rank
from gemma_research.metrics.scoring import hit_at_k, reciprocal_rank

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = (
    ROOT / "manifests/raw_data/gemma4/models/google/gemma-4/gguf/"
    "gemma-4-e2b-it-qat-q4_0-gguf/2/gemma-4-E2B_q4_0-it.gguf"
)
OUT = ROOT / "results/gemma_v2"
SEVERITIES = (0.0, 0.5)
POOL = 15


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    calls = OUT / "calls.jsonl"
    done = set()
    if calls.exists():
        for line in calls.read_text().splitlines():
            d = json.loads(line)
            done.add((d["task_id"], d["severity"]))
    config = yaml.safe_load((ROOT / "configs/pilot_a.yaml").read_text())
    df = load_loc_bench(str(ROOT / config["loc_bench_parquet"]), tuple(config["repos"]))
    llm = Llama(model_path=str(MODEL_PATH), n_ctx=4096, n_threads=12, verbose=False)
    grammar = LlamaGrammar.from_string(indexed_grammar_text())
    t_start = time.perf_counter()
    for repo in config["repos"]:
        for commit, commit_rows in df[df["repo"] == repo].groupby("base_commit"):
            graph, _ = build_graph_from_source(repo, commit, fetch_repo_snapshot(repo, commit))
            tasks, _ = build_tasks_for_commit(commit_rows, graph, repo, commit)
            tasks = [t for t in tasks if not is_dev_split(t.task_id, config["dev_fraction"])]
            if all((t.task_id, s) in done for t in tasks for s in SEVERITIES):
                continue
            index = BM25Index(graph.nodes)
            for task in tasks:
                for sev in SEVERITIES:
                    if (task.task_id, sev) in done:
                        continue
                    g = graph if sev == 0.0 else missing_edges(graph, sev, 1)[0]
                    fh = fixed_hybrid_rank(g, task.query_text, bm25_index=index)
                    bm = bm25_rank(g, task.query_text, index=index)
                    res = gemma_rerank_indexed(llm, g, task.query_text, POOL, index, grammar)
                    gold = task.gold_node_ids
                    rec = {
                        "repo": repo, "task_id": task.task_id, "severity": sev,
                        "pool_recall": float(any(c in gold for c in res.candidate_pool)),
                        "n_parsed_valid": res.n_parsed_valid, "raw_output": res.raw_output,
                        "runtime_seconds": res.runtime_seconds,
                        "prompt_tokens": res.prompt_tokens, "completion_tokens": res.completion_tokens,
                        "hit5": {"gemma": hit_at_k(res.ranking, gold, 5), "fixed_hybrid": hit_at_k(fh, gold, 5),
                                 "bm25": hit_at_k(bm, gold, 5)},
                        "hit1": {"gemma": hit_at_k(res.ranking, gold, 1), "fixed_hybrid": hit_at_k(fh, gold, 1),
                                 "bm25": hit_at_k(bm, gold, 1)},
                        "mrr": {"gemma": reciprocal_rank(res.ranking, gold), "fixed_hybrid": reciprocal_rank(fh, gold),
                                "bm25": reciprocal_rank(bm, gold)},
                    }
                    with calls.open("a") as f:
                        f.write(json.dumps(rec) + "\n")
                    print(task.task_id, sev, rec["hit5"], res.n_parsed_valid, f"{res.runtime_seconds:.0f}s", flush=True)
    (OUT / "run_manifest.json").write_text(json.dumps({
        "generation_params": GENERATION_PARAMS, "pool_size": POOL, "severities": SEVERITIES,
        "model_sha256": json.loads((ROOT / "manifests/gemma4_manifest.json").read_text())["sha256"],
        "wall_seconds_last_invocation": time.perf_counter() - t_start}, indent=1))


if __name__ == "__main__":
    main()
