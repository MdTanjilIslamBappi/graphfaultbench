"""Paired method differences with repository-clustered bootstrap, per-repo results.

Independent of src/ (stdlib only). Resampling unit = repository (6 clusters), so
intervals are very wide by design; reported as descriptive, not as tests.
Usage: python scripts/paired_analysis.py [results_dir ...] -> results/analysis/paired_differences.json
"""
import collections
import csv
import json
import random
import sys
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parent.parent
dirs = sys.argv[1:] or ["results/pilot"]
require("paired_analysis.py", *[f"{d}/metrics.csv" for d in dirs])
rows = []
for d in dirs:
    with open(ROOT / d / "metrics.csv") as f:
        rows += list(csv.DictReader(f))

PAIRS = [("fixed_hybrid", "bm25"), ("graph_expansion", "bm25"), ("repomap", "bm25")]
rng = random.Random(20261022)
B = 5000

def cluster_boot(by_repo):
    """by_repo: {repo: [paired diffs]}. Resample repos, then take mean of all diffs (task-weighted)."""
    repos = list(by_repo)
    est = sum(sum(v) for v in by_repo.values()) / sum(len(v) for v in by_repo.values())
    stats = []
    for _ in range(B):
        s = [by_repo[rng.choice(repos)] for _ in repos]
        n = sum(len(v) for v in s)
        stats.append(sum(sum(v) for v in s) / n)
    stats.sort()
    return est, stats[int(.025 * B)], stats[int(.975 * B)]

idx = collections.defaultdict(dict)
for r in rows:
    idx[(r["operator"], r["severity"], r["task_id"], r["seed"], r["repo"])][r["method"]] = float(r["hit_at_5"])

out = {"resampling_unit": "repository", "n_boot": B, "metric": "hit_at_5 (paired difference, A - B)", "results": []}
ops = sorted({k[0] for k in idx})
for op in ops:
    for sev in sorted({k[1] for k in idx if k[0] == op}, key=float):
        for a, b in PAIRS:
            by_repo = collections.defaultdict(list)
            for k, m in idx.items():
                if k[0] == op and k[1] == sev and a in m and b in m:
                    by_repo[k[4]].append(m[a] - m[b])
            if not by_repo:
                continue
            est, lo, hi = cluster_boot(by_repo)
            n = sum(len(v) for v in by_repo.values())
            per_repo = {r: round(sum(v) / len(v), 3) for r, v in sorted(by_repo.items())}
            out["results"].append({"operator": op, "severity": float(sev), "A": a, "B": b, "n_rows": n,
                                   "mean_diff": round(est, 4), "ci95": [round(lo, 4), round(hi, 4)],
                                   "per_repo_mean_diff": per_repo})
Path(ROOT / "results/analysis").mkdir(exist_ok=True)
name = "paired_differences.json" if dirs == ["results/pilot"] else "paired_differences_" + "_".join(Path(d).name for d in dirs) + ".json"
(ROOT / "results/analysis" / name).write_text(json.dumps(out, indent=1))
for r in out["results"]:
    if r["severity"] in (0.0, 0.75) or r["operator"] == "healthy_control":
        print(r["operator"], r["severity"], r["A"], "-", r["B"], r["n_rows"], r["mean_diff"], r["ci95"])
