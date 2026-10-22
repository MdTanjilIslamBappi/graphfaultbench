"""Audit the MRR change in the post hoc repomap correction (reads stored rankings only).

Gold ids are not stored, but MRR is the reciprocal of the gold rank in the full
ranking, so the rank is 1 / mrr. Checks: integrality of 1/mrr, consistency of
hit@5 with rank <= 5, per-severity denominators, and a decomposition of the MRR
difference by original rank bucket.
"""
import collections
import json
import sys
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parents[1]
BUCKETS = [(1, 1), (2, 3), (4, 5), (6, 10), (11, 10**9)]


def bucket(rank: int) -> str:
    for lo, hi in BUCKETS:
        if lo <= rank <= hi:
            return f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
    raise ValueError(rank)


def main() -> None:
    require("analyse_repomap_mrr.py", "results/repomap_correction/pilot_a/rankings.jsonl")
    out: dict = {}
    base = ROOT / "results" / "repomap_correction"
    sets = {"pilot_a": [base / "pilot_a"], "holdout": sorted(base.glob("holdout_*"))}
    for cfg, dirs in sets.items():
        lines = [ln for d in dirs for ln in (d / "rankings.jsonl").read_text().splitlines()]
        by: dict = collections.defaultdict(dict)
        problems = []
        for line in lines:
            r = json.loads(line)
            rank_f = 1.0 / r["mrr"] if r["mrr"] > 0 else None
            rank = round(rank_f) if rank_f else None
            if rank is not None and abs(rank_f - rank) > 1e-6:
                problems.append(("non-integral rank", r["task_id"], r["method"]))
            if rank is not None and (rank <= 5) != (r["hit_at_5"] == 1.0):
                problems.append(("hit@5 inconsistent", r["task_id"], r["method"]))
            top10 = r["top10"]
            if sum(x.startswith("__DANGLING__:") for x in top10[:5]) != r["dangling_in_top5"]:
                problems.append(("dangling5 mismatch", r["task_id"], r["method"]))
            r["rank"] = rank
            by[(r["task_id"], r["severity"], r["seed"])][r["method"]] = r
        res = {"problems": problems, "severities": {}}
        for sev in sorted({k[1] for k in by}):
            ks = [k for k in by if k[1] == sev]
            n = len(ks)
            assert all(len(by[k]) == 2 for k in ks)
            mo = sum(by[k]["repomap_original"]["mrr"] for k in ks) / n
            mc = sum(by[k]["repomap_corrected"]["mrr"] for k in ks) / n
            dec = collections.defaultdict(float)
            moved = 0
            top1_changed = 0
            for k in ks:
                o, c = by[k]["repomap_original"], by[k]["repomap_corrected"]
                dec[bucket(o["rank"])] += (c["mrr"] - o["mrr"]) / n
                if o["rank"] != c["rank"]:
                    moved += 1
                if o["top10"][0] != c["top10"][0]:
                    top1_changed += 1
            res["severities"][str(sev)] = {
                "n": n,
                "mrr_original": mo,
                "mrr_corrected": mc,
                "mrr_difference": mc - mo,
                "gold_rank_changed": moved,
                "top1_node_changed": top1_changed,
                "difference_by_original_gold_rank": dict(dec),
                "gold_rank_lower_bound_1_in_original": sum(
                    by[k]["repomap_original"]["rank"] == 1 for k in ks
                ),
            }
        out[cfg] = res
    dest = ROOT / "results" / "analysis" / "repomap_mrr_audit.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    json.dump(out, sys.stdout, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
