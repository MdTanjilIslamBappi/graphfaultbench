"""Exact (enumerated) repository-cluster bootstrap for the holdout healthy-graph difference fixed_hybrid - bm25.

All 6^6 = 46,656 ordered repository draws are enumerated, so there is no Monte-Carlo error and no seed.
Stdlib only.  Usage: python3 scripts/audit_holdout_ci.py -> results/analysis/holdout_exact_bootstrap.json
"""
import csv
import glob
import itertools
import json
from collections import defaultdict
from pathlib import Path

from _inputs import require

R = Path(__file__).resolve().parent.parent / "results"
require("audit_holdout_ci.py", "results/holdout_django/metrics.csv")
rows = []
for d in sorted(glob.glob(str(R / "holdout_*"))):
    if Path(d, "metrics.csv").exists():
        with open(Path(d) / "metrics.csv") as f:
            rows += list(csv.DictReader(f))
h = defaultdict(dict)
for r in rows:
    if r["operator"] == "healthy_control" and r["method"] in ("fixed_hybrid", "bm25"):
        h[(r["repo"], r["task_id"])][r["method"]] = float(r["hit_at_5"])
by = defaultdict(list)
for (repo, _), v in h.items():
    by[repo].append(v["fixed_hybrid"] - v["bm25"])
repos = sorted(by)
if not repos:
    raise SystemExit("audit_holdout_ci.py: no healthy-control rows found in results/holdout_*/metrics.csv")
vals = []
for draw in itertools.product(repos, repeat=len(repos)):
    xs = [x for r in draw for x in by[r]]
    vals.append(sum(xs) / len(xs))
vals.sort()
n = len(vals)
est = sum(x for v in by.values() for x in v) / sum(len(v) for v in by.values())
out = {
    "n_tasks": sum(len(v) for v in by.values()), "estimate": est,
    "per_repo_sum_diff": {r: sum(by[r]) for r in repos},
    "tasks_fh_better_bm25_better": [sum(x > 0 for v in by.values() for x in v), sum(x < 0 for v in by.values() for x in v)],
    "draws": n, "share_of_draws_exactly_zero": sum(v == 0 for v in vals) / n,
    "share_of_draws_negative": sum(v < 0 for v in vals) / n,
    "percentile_ci95": [vals[int(0.025 * n)], vals[int(0.975 * n) - 1]],
}
(R / "analysis/holdout_exact_bootstrap.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
