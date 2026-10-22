"""Independent audit of the Gemma v2 reranking result (no model is loaded, no API is called).

Rebuilds each call's candidate pool and gold labels from the commit-pinned source, re-parses the stored
raw_output with a separate parser, applies the documented fallback (picked ids first, then remaining pool
ids in pool order) and rescores hit@1/hit@5. Compares with the flags stored by the original run.
Writes results/gemma_v2/audit.json.  Usage: uv run python scripts/audit_reranker.py
"""
from __future__ import annotations

import collections
import json
import random
from pathlib import Path

import yaml
from _inputs import require

from gemma_research.data.graph_builder import build_graph_from_source
from gemma_research.data.loc_bench_tasks import build_tasks_for_commit, is_dev_split, load_loc_bench
from gemma_research.data.repo_source import fetch_repo_snapshot
from gemma_research.evidence.perturb import missing_edges
from gemma_research.evidence.retrieve import BM25Index, fixed_hybrid_rank

ROOT = Path(__file__).resolve().parent.parent
POOL = 15


def parse(raw: str, n_pool: int) -> list[int]:
    """Indices (0-based) of distinct in-range numbers, first five, in output order."""
    out: list[int] = []
    for tok in raw.split("\n"):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= n_pool and int(tok) - 1 not in out:
            out.append(int(tok) - 1)
        if len(out) == 5:
            break
    return out


def hit(ids: list[str], gold: set[str], k: int) -> int:
    return int(any(i in gold for i in ids[:k]))


def boot_ci(by_unit: dict, B: int = 5000, seed: int = 20261022):
    rng = random.Random(seed)
    units = list(by_unit)
    est = sum(sum(v) for v in by_unit.values()) / sum(len(v) for v in by_unit.values())
    s = []
    for _ in range(B):
        pick = [by_unit[rng.choice(units)] for _ in units]
        s.append(sum(sum(v) for v in pick) / sum(len(v) for v in pick))
    s.sort()
    return est, s[int(0.025 * B)], s[int(0.975 * B)]


def main() -> None:
    require("audit_reranker.py", "results/gemma_v2/calls.jsonl")
    with open(ROOT / "results/gemma_v2/calls.jsonl") as f:
        stored = {(c["task_id"], c["severity"]): c for c in map(json.loads, f)}
    config = yaml.safe_load((ROOT / "configs/pilot_a.yaml").read_text())
    df = load_loc_bench(str(ROOT / config["loc_bench_parquet"]), tuple(config["repos"]))
    rows = []
    for repo in config["repos"]:
        for commit, commit_rows in df[df["repo"] == repo].groupby("base_commit"):
            graph, _ = build_graph_from_source(repo, commit, fetch_repo_snapshot(repo, commit))
            tasks, _ = build_tasks_for_commit(commit_rows, graph, repo, commit)
            tasks = [t for t in tasks if not is_dev_split(t.task_id, config["dev_fraction"])]
            index = BM25Index(graph.nodes)
            for t in tasks:
                for sev in (0.0, 0.5):
                    if (t.task_id, sev) not in stored:
                        continue
                    g = graph if sev == 0.0 else missing_edges(graph, sev, 1)[0]
                    rank = [c.node_id for c in fixed_hybrid_rank(g, t.query_text, bm25_index=index)]
                    pool = rank[:POOL]
                    gold = set(t.gold_node_ids)
                    rec = stored[(t.task_id, sev)]
                    idx = parse(rec["raw_output"], len(pool))
                    picked = [pool[i] for i in idx]
                    gem = picked + [p for p in pool if p not in picked]  # fallback = pool order
                    rows.append({
                        "repo": repo, "task": t.task_id, "sev": sev, "n_valid": len(idx),
                        "n_lines": len(rec["raw_output"].split("\n")),
                        "n_dup_or_oor": len(rec["raw_output"].split("\n")) - len(idx),
                        "pool_has_gold": int(any(p in gold for p in pool)),
                        "gem5": hit(gem, gold, 5), "fh5": hit(rank, gold, 5),
                        "gem1": hit(gem, gold, 1), "fh1": hit(rank, gold, 1),
                        "gem5_no_fallback": hit(picked, gold, 5),  # picked ids only, no fill
                        "stored_gem5": rec["hit5"]["gemma"], "stored_fh5": rec["hit5"]["fixed_hybrid"],
                        "stored_gem1": rec["hit1"]["gemma"], "stored_pool": rec["pool_recall"],
                        "stored_nvalid": rec["n_parsed_valid"],
                    })
    n = len(rows)
    mism = {k: sum(r[a] != r[b] for r in rows) for k, (a, b) in {
        "gem5": ("gem5", "stored_gem5"), "fh5": ("fh5", "stored_fh5"), "gem1": ("gem1", "stored_gem1"),
        "pool": ("pool_has_gold", "stored_pool"), "nvalid": ("n_valid", "stored_nvalid")}.items()}
    S = lambda rs, k: sum(r[k] for r in rs)
    out = {"n_rows_rescored": n, "n_stored": len(stored), "mismatches_vs_stored": mism,
           "valid_id_histogram": dict(collections.Counter(r["n_valid"] for r in rows)),
           "mean_valid_ids": sum(r["n_valid"] for r in rows) / n,
           "counts": {k: S(rows, k) for k in ("gem5", "fh5", "gem1", "fh1", "pool_has_gold", "gem5_no_fallback")}}
    # discordance (call level)
    out["discordant_calls"] = {"gem_only": sum(r["gem5"] > r["fh5"] for r in rows),
                               "fh_only": sum(r["gem5"] < r["fh5"] for r in rows)}
    # strata: well-formed vs malformed
    for name, sel in (("wellformed_5of5", lambda r: r["n_valid"] == 5), ("malformed_lt5", lambda r: r["n_valid"] < 5)):
        rs = [r for r in rows if sel(r)]
        out[name] = {"n": len(rs), "gem5": S(rs, "gem5"), "fh5": S(rs, "fh5"), "gem1": S(rs, "gem1"),
                     "fh1": S(rs, "fh1"), "pool_has_gold": S(rs, "pool_has_gold"),
                     "gem5_no_fallback": S(rs, "gem5_no_fallback")}
    # units: call (as originally), task (mean over the two severities), healthy only
    def paired(rs, key="repo", a="gem5", b="fh5"):
        by = collections.defaultdict(list)
        for r in rs:
            by[r[key]].append(r[a] - r[b])
        return boot_ci(by)
    out["paired_hit5_call_unit_repo_cluster"] = paired(rows)
    out["paired_hit1_call_unit_repo_cluster"] = paired(rows, a="gem1", b="fh1")
    # task-level: average severities per task first, then cluster by repo
    bytask = collections.defaultdict(list)
    for r in rows:
        bytask[(r["repo"], r["task"])].append(r["gem5"] - r["fh5"])
    byrepo = collections.defaultdict(list)
    for (repo, _), v in bytask.items():
        byrepo[repo].append(sum(v) / len(v))
    out["paired_hit5_task_unit_repo_cluster"] = boot_ci(byrepo)
    out["tasks_gem_better_fh_better_tie"] = [
        sum(sum(v) > 0 for v in bytask.values()), sum(sum(v) < 0 for v in bytask.values()),
        sum(sum(v) == 0 for v in bytask.values())]
    # pool-limited contrast: restrict to calls whose pool contains gold (only place a reranker can help)
    pg = [r for r in rows if r["pool_has_gold"]]
    out["pool_has_gold_subset"] = {"n": len(pg), "gem5": S(pg, "gem5"), "fh5": S(pg, "fh5"),
                                   "paired": paired(pg)}
    # post-hoc null: expected hit@5 if five pool ids were chosen at random (needs per-call gold-in-pool count,
    # approximated here by the one-gold-in-pool case; reported only as context)
    out["note"] = "random-5-of-15 reference is 1/3 of pool_has_gold calls if one gold id is in the pool"
    out["random_ref_hit5_if_single_gold_in_pool"] = S(rows, "pool_has_gold") * 5 / 15
    (ROOT / "results/gemma_v2/audit.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
