"""Per-interval table of stored (Monte Carlo) versus exact-enumeration cluster-bootstrap CIs.

Estimand and design are identical in both: resample whole repositories with
replacement and take the row-pooled mean (marginal cells) or mean paired
difference (paired intervals). The exact version enumerates all k^k ordered
repository draws instead of sampling 2,000. Reads stored artefacts only.
Usage: python3 scripts/exact_ci_table.py -> results/analysis/exact_ci_table.json
"""

import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parent.parent
require("exact_ci_table.py", "results/pilot/metrics.csv", "results/gemma_v2/calls.jsonl")


def rows_of(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def exact(by):
    cl = [v for v in by.values() if v]
    vals = []
    for d in itertools.product(range(len(cl)), repeat=len(cl)):
        xs = [x for i in d for x in cl[i]]
        vals.append(sum(xs) / len(xs))
    vals.sort()
    n = len(vals)
    return [vals[int(0.025 * n)], vals[int(0.975 * n) - 1]]


out = {"marginal": {}, "paired": {}}
for d in ["pilot", "coverage_floor_eval", "stale_rewire_eval"]:
    with open(ROOT / "results" / d / "summary.json") as fh:
        summ = json.load(fh)
    cells = defaultdict(lambda: defaultdict(list))
    for r in rows_of(ROOT / "results" / d / "metrics.csv"):
        if "any_gold_hidden" in r and str(r["any_gold_hidden"]).lower() in ("1", "1.0", "true"):
            continue
        sev = float(r["severity"])
        cells[f"{r['method']}@{r['operator']}@severity={sev}"][r["repo"]].append(float(r["hit_at_5"]))
        cells[f"{r['method']}@severity={sev}"][r["repo"]].append(float(r["hit_at_5"]))
    out["marginal"][d] = {}
    for k, by in cells.items():
        if k in summ:
            s = summ[k].get("metrics", {}).get("hit_at_5", summ[k])
            out["marginal"][d][k] = {"stored": [s["ci_low"], s["ci_high"]], "exact": exact(by),
                                      "n_rows": sum(len(v) for v in by.values())}
HO = ["holdout_sqlglot", "holdout_ytdlp", "holdout_django", "holdout_moto", "holdout_sympy", "holdout_matplotlib"]
for name, dirs in (("pilot", ["pilot"]), ("holdout", HO)):
    f = next((ROOT / "results/analysis").glob("paired_differences.json" if name == "pilot" else "paired_differences_holdout*.json"))
    idx = defaultdict(dict)
    for dd in dirs:
        for r in rows_of(ROOT / "results" / dd / "metrics.csv"):
            idx[(r["operator"], r["severity"], r["task_id"], r["seed"], r["repo"])][r["method"]] = float(r["hit_at_5"])
    out["paired"][name] = []
    with open(f) as fh:
        stored_results = json.load(fh)["results"]
    for e in stored_results:
        by = defaultdict(list)
        for k, m in idx.items():
            if k[0] == e["operator"] and float(k[1]) == e["severity"] and e["A"] in m and e["B"] in m:
                by[k[4]].append(m[e["A"]] - m[e["B"]])
        out["paired"][name].append({"A": e["A"], "B": e["B"], "operator": e["operator"], "severity": e["severity"],
                                     "estimate": e.get("diff", e.get("estimate")), "stored": e["ci95"], "exact": exact(by)})
out["gemma_v2"] = {}
with open(ROOT / "results/gemma_v2/calls.jsonl") as fh:
    calls = [json.loads(line) for line in fh]
for label, sev in (("all", None), ("severity_0.0", 0.0), ("severity_0.5", 0.5)):
    for other in ("fixed_hybrid", "bm25"):
        by = defaultdict(list)
        for c in calls:
            if sev is None or c["severity"] == sev:
                by[c["repo"]].append(c["hit5"]["gemma"] - c["hit5"][other])
        n = sum(len(v) for v in by.values())
        out["gemma_v2"][f"{label}:gemma-{other}"] = {"n": n, "estimate": sum(sum(v) for v in by.values()) / n, "exact": exact(by)}
(ROOT / "results/analysis/exact_ci_table.json").write_text(json.dumps(out, indent=1))
print({k: (len(v) if isinstance(v, list) else {a: len(b) for a, b in v.items()}) for k, v in out.items()})
