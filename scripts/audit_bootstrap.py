"""Controlled comparison of bootstrap implementations on identical observations (stdlib + src scoring for the stored function).

For every cell of results/<dir>/summary.json (marginal hit@5, repository-cluster bootstrap) compute:
  stored   : src bootstrap_ci_clustered, 2000 resamples, seed 0 (the run's own call; re-executed here)
  exact    : all 6^k ordered repository draws (k = #repos), no Monte-Carlo error
  mc5000   : the independent scripts' style (5000 resamples, random.Random(20261022), index int(.975*B), no -1)
Usage: python3 scripts/audit_bootstrap.py -> results/analysis/bootstrap_audit.json
"""
import csv
import itertools
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
require("audit_bootstrap.py", "results/pilot/metrics.csv")
from gemma_research.metrics.scoring import bootstrap_ci_clustered


def _csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _json(path):
    with open(path) as f:
        return json.load(f)


def exact(by):
    cl = [v for v in by.values() if v]
    vals = []
    for d in itertools.product(range(len(cl)), repeat=len(cl)):
        xs = [x for i in d for x in cl[i]]
        vals.append(sum(xs) / len(xs))
    vals.sort()
    n = len(vals)
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def mc(by, B=5000):
    rng = random.Random(20261022)
    cl = [v for v in by.values() if v]
    st = []
    for _ in range(B):
        s = [cl[rng.randrange(len(cl))] for _ in cl]
        xs = [x for c in s for x in c]
        st.append(sum(xs) / len(xs))
    st.sort()
    return st[int(0.025 * B)], st[int(0.975 * B)]


res = {}
for d in ["pilot", "coverage_floor_eval", "stale_rewire_eval"]:
    rows = _csv(ROOT / "results" / d / "metrics.csv")
    summ = _json(ROOT / "results" / d / "summary.json")
    cells = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if "any_gold_hidden" in r and str(r["any_gold_hidden"]).lower() in ("1", "1.0", "true"):
            continue  # coverage-floor summaries score the gold-visible subset only
        sev = float(r["severity"])
        cells[f"{r['method']}@{r['operator']}@severity={sev}"][r["repo"]].append(float(r["hit_at_5"]))
        cells[f"{r['method']}@severity={sev}"][r["repo"]].append(float(r["hit_at_5"]))  # coverage-floor key form
    out = []
    for k, by in cells.items():
        if k not in summ:
            continue
        st = bootstrap_ci_clustered(dict(by), n_resamples=2000, seed=0)
        e, m = exact(by), mc(by)
        s = summ[k].get("metrics", {}).get("hit_at_5", summ[k])
        out.append({"cell": k, "stored_json": [s["ci_low"], s["ci_high"]], "rerun_stored_fn": [st.low, st.high],
                    "exact": list(e), "mc5000": list(m)})
    res[d] = {
        "n_cells": len(out),
        "stored_json_vs_rerun_max_abs": max(max(abs(o["stored_json"][0] - o["rerun_stored_fn"][0]), abs(o["stored_json"][1] - o["rerun_stored_fn"][1])) for o in out),
        "stored_vs_exact_max_abs": max(max(abs(o["rerun_stored_fn"][i] - o["exact"][i]) for i in (0, 1)) for o in out),
        "mc5000_vs_exact_max_abs": max(max(abs(o["mc5000"][i] - o["exact"][i]) for i in (0, 1)) for o in out),
        "worst_cell_stored_vs_exact": max(out, key=lambda o: max(abs(o["rerun_stored_fn"][i] - o["exact"][i]) for i in (0, 1))),
    }
(ROOT / "results/analysis/bootstrap_audit.json").write_text(json.dumps(res, indent=1))
for d, v in res.items():
    print(d, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in v.items() if k != "worst_cell_stored_vs_exact"})
    print("  worst:", v["worst_cell_stored_vs_exact"])

# ---- paired differences (the intervals used for method comparisons in the paper) ----
paired = {}
for name, dirs in (("paired_differences.json", ["pilot"]),
                   ("paired_differences_holdout_sqlglot_holdout_ytdlp_holdout_django_holdout_moto_holdout_sympy_holdout_matplotlib.json",
                    ["holdout_sqlglot", "holdout_ytdlp", "holdout_django", "holdout_moto", "holdout_sympy", "holdout_matplotlib"])):
    f = ROOT / "results/analysis" / name
    if not f.exists():
        continue
    stored = _json(f)["results"]
    rows = []
    for d in dirs:
        rows += _csv(ROOT / "results" / d / "metrics.csv")
    idx = defaultdict(dict)
    for r in rows:
        idx[(r["operator"], r["severity"], r["task_id"], r["seed"], r["repo"])][r["method"]] = float(r["hit_at_5"])
    worst, n = 0.0, 0
    for e in stored:
        by = defaultdict(list)
        for k, m in idx.items():
            if k[0] == e["operator"] and float(k[1]) == e["severity"] and e["A"] in m and e["B"] in m:
                by[k[4]].append(m[e["A"]] - m[e["B"]])
        lo, hi = exact(by)
        worst = max(worst, abs(lo - e["ci95"][0]), abs(hi - e["ci95"][1]))
        n += 1
    paired[name[:40]] = {"n_intervals": n, "max_abs_stored_vs_exact": round(worst, 4)}
print("paired:", paired)
res["paired"] = paired
(ROOT / "results/analysis/bootstrap_audit.json").write_text(json.dumps(res, indent=1))
