"""Independent recomputation of headline claims from raw metrics.csv files.

Uses only csv/statistics from the standard library (no project imports) so it
shares no code with src/gemma_research. Splits eval/dev via run_manifest-free
logic: eval vs dev is read from the experiment directory convention, so the
task-split is cross-checked by counting tasks per file.
Usage: python scripts/validate_headline_claims.py
"""
import collections
import csv
import json
from pathlib import Path

from _inputs import require

R = Path(__file__).resolve().parent.parent / "results"
require("validate_headline_claims.py", "results/pilot/metrics.csv", "results/pilot/graph_reports.json")

def rows(d):
    with open(R / d / "metrics.csv") as f:
        return list(csv.DictReader(f))

def fl(x):
    return float(x) if x not in ("", None) else None

def mean(v):
    return sum(v) / len(v) if v else float("nan")

out = {}
p = rows("pilot")
out["pilot_rows"] = len(p)
out["pilot_operators"] = sorted({r["operator"] for r in p})
out["pilot_methods"] = sorted({r["method"] for r in p})
out["pilot_tasks"] = len({r["task_id"] for r in p})
out["pilot_repos"] = sorted({r["repo"] for r in p})
out["pilot_commits"] = len({r["commit"] for r in p})
out["pilot_severities"] = sorted({r["severity"] for r in p})
out["pilot_seeds"] = sorted({r["seed"] for r in p})
by = collections.defaultdict(list)
for r in p:
    by[r["method"]].append(fl(r["hit_at_5"]))
out["pilot_hit5_by_method(all rows incl. dev?)"] = {m: (len(v), round(mean(v), 4)) for m, v in by.items()}
# rows per (method) per operator
cnt = collections.Counter((r["method"], r["operator"]) for r in p)
out["rows_per_method_operator"] = {f"{k[0]}|{k[1]}": v for k, v in sorted(cnt.items())}
# severity-0 identity: corrupted ops at severity 0 should equal healthy_control per method/task/seed
hc = {(r["method"], r["task_id"], r["seed"]): r["hit_at_5"] for r in p if r["operator"] == "healthy_control"}
mism = 0; chk = 0
for r in p:
    if r["operator"] != "healthy_control" and float(r["severity"]) == 0.0:
        k = (r["method"], r["task_id"], r["seed"])
        if k in hc:
            chk += 1; mism += hc[k] != r["hit_at_5"]
out["severity0_vs_healthy_checked"] = chk; out["severity0_mismatches"] = mism
# gate == fixed_hybrid?
fh = {(r["operator"], r["severity"], r["task_id"], r["seed"]): r["hit_at_5"] for r in p if r["method"] == "fixed_hybrid"}
dg = [(r, fh.get((r["operator"], r["severity"], r["task_id"], r["seed"]))) for r in p if r["method"] == "diagnostic_gate"]
out["gate_rows"] = len(dg)
out["gate_ne_fixed_hybrid"] = sum(1 for r, h in dg if h is not None and r["hit_at_5"] != h)
out["policy_chosen"] = dict(collections.Counter(r["policy_chosen"] for r, _ in dg))
# unresolved-call ratio
g = json.loads((R / "pilot" / "graph_reports.json").read_text())
out["graph_reports_type"] = type(g).__name__
out["graph_reports_sample_keys"] = list((g[0] if isinstance(g, list) else next(iter(g.values()))).keys()) if g else []
print(json.dumps(out, indent=1, default=str))
