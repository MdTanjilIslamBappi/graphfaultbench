"""Stdlib recomputation of the Phase 1-5 and stale_rewire claims in the manuscript from raw metrics.csv files.

Shares no code with src/. Each check prints PASS/FAIL against the manuscript's stated value.
Usage: python3 scripts/audit_phases.py  -> results/analysis/phase_audit.json
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from _inputs import require

R = Path(__file__).resolve().parent.parent / "results"
require("audit_phases.py", "results/pilot/metrics.csv", "results/pilot/graph_reports.json", "results/pilot/gold_resolution_reports.json")
checks = []


def rd(d):
    with open(R / d / "metrics.csv") as f:
        return list(csv.DictReader(f))


def chk(name, got, want, tol=0.0005):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    checks.append({"claim": name, "recomputed": got, "manuscript": want, "pass": bool(ok)})


def mean(v):
    return sum(v) / len(v)


def boot(by_repo, B=5000, seed=20261022):
    rng = random.Random(seed)
    repos = list(by_repo)
    s = []
    for _ in range(B):
        pick = [by_repo[rng.choice(repos)] for _ in repos]
        s.append(mean([x for v in pick for x in v]))
    s.sort()
    return s[int(.025 * B)], s[int(.975 * B)]


# ---- Pilot / Phase 1-2
p = rd("pilot")
man = json.loads((R / "pilot/run_manifest.json").read_text())
chk("pilot scoring rows", len(p), 8100)
chk("n_eval_tasks", man["n_eval_tasks"], 54)
chk("n_dev_tasks", man["n_dev_tasks"], 10)
chk("excluded tasks", man["n_excluded_tasks"], 1)
chk("wall minutes set1", round(man["total_wall_seconds_set1"] / 60), 69)
chk("wall minutes set2", round(man["total_wall_seconds_set2"] / 60), 53)
chk("peak RSS GiB", round(man["peak_rss_kb"] / 1024 / 1024, 2), 1.21, 0.005)
gr = json.loads((R / "pilot/graph_reports.json").read_text())
chk("distinct commits (graph reports)", len({(g["repo"], g["commit"]) for g in gr}), 58)
rep = json.loads((R / "pilot/gold_resolution_reports.json").read_text())
chk("rows attempted", sum(r["n_rows_for_commit"] for r in rep), 65)
chk("rows resolved", sum(r["n_resolved"] for r in rep), 64)
exc = [i for r in rep for i in r["excluded_instance_ids"]]
chk("excluded ids (count)", len(exc), 1)
chk("seeds", sorted({r["seed"] for r in p}), ["1", "2", "3"])
chk("operators", sorted({r["operator"] for r in p}),
    ["healthy_control", "high_centrality_edges", "missing_edges", "stale_symbol_refs"])

# eval tasks = those in set of 54; derive from manifest-free rule: pilot has dev tasks? use summary
ev_ids = set()
for k in ("pilot_set1", "pilot_set2"):
    pass
# eval/dev flag is not in the CSV: the pilot CSV rows are eval tasks only when the count is 54
tasks = {r["task_id"] for r in p}
chk("tasks in pilot csv", len(tasks), 54)

h = [r for r in p if r["operator"] == "healthy_control"]
for m, want in (("bm25", 18), ("fixed_hybrid", 18), ("graph_expansion", 16), ("repomap", 15)):
    bys = defaultdict(dict)
    for r in h:
        if r["method"] == m:
            bys[r["task_id"]].setdefault(r["seed"], float(r["hit_at_5"]))
    chk(f"healthy hit@5 tasks solved {m}", int(sum(max(v.values()) for v in bys.values())), want)
    chk(f"healthy hit@5 seed-invariant {m}", all(len(set(v.values())) == 1 for v in bys.values()), True)
# paired healthy difference + clustered CI
def task_hit(m):
    d = {}
    for r in h:
        if r["method"] == m:
            d[(r["repo"], r["task_id"])] = float(r["hit_at_5"])
    return d
a, b = task_hit("fixed_hybrid"), task_hit("bm25")
by = defaultdict(list)
for k in a:
    by[k[0]].append(a[k] - b[k])
lo, hi = boot(by)
chk("healthy paired diff", mean([x for v in by.values() for x in v]), 0.0)
chk("healthy CI low", lo, -0.056, 0.01)
chk("healthy CI high", hi, 0.041, 0.01)

# Phase 2: corrupted rows
mx = defaultdict(list)
for r in p:
    if r["operator"] != "healthy_control" or True:
        mx[r["method"]].append(r)
corr = [r for r in p if r["operator"] != "healthy_control"]
cm = defaultdict(list)
for r in corr:
    cm[r["method"]].append(float(r["hit_at_5"]))
chk("corrupted rows per method", len(cm["bm25"]), 1458)
allm = defaultdict(list)
for r in p:
    allm[r["method"]].append(float(r["hit_at_5"]))
chk("scored rows per method", len(allm["bm25"]), 1620)
chk("bm25 mean hit@5", mean(allm["bm25"]), 0.333)
chk("fixed_hybrid mean hit@5", mean(allm["fixed_hybrid"]), 0.338)
chk("gate mean hit@5", mean(allm["diagnostic_gate"]), 0.338)
fh = {(r["task_id"], r["operator"], r["severity"], r["seed"]): r["hit_at_5"] for r in p if r["method"] == "fixed_hybrid"}
g = [r for r in p if r["method"] == "diagnostic_gate"]
chk("gate rows != fixed_hybrid", sum(fh[(r["task_id"], r["operator"], r["severity"], r["seed"])] != r["hit_at_5"] for r in g), 0)
chk("gate hybrid rows", sum(r["policy_chosen"] == "hybrid" for r in g), 1620)
chk("node_coverage all 1.0", all(float(r["node_coverage"]) == 1.0 for r in g), True)
chk("anchor_confidence all 1.0", all(float(r["anchor_confidence"]) == 1.0 for r in g), True)
iso = defaultdict(list)
for r in g:
    iso[(r["operator"], r["severity"])].append(float(r["isolated_node_rate"]))
chk("isolated rate healthy", mean(iso[("healthy_control", "0.0")]), 0.003, 0.0005)
chk("isolated rate missing_edges sev 0.75 mean", mean(iso[("missing_edges", "0.75")]), 0.360, 0.0005)
chk("isolated rate high_centrality sev 0.75 mean", mean(iso[("high_centrality_edges", "0.75")]), 0.267, 0.0005)
chk("isolated rate stale_symbol_refs sev 0.75 mean", mean(iso[("stale_symbol_refs", "0.75")]), 0.122, 0.0005)
chk("isolated rate max single row", max(x for v in iso.values() for x in v), 0.423, 0.0005)
chk("isolated rate never reaches 0.5", max(x for v in iso.values() for x in v) < 0.5, True)

# ---- Phase 3
d = rd("node_omission_dev")
chk("phase3 rows", len(d), 120)
by_s = defaultdict(list)
for r in d:
    by_s[r["severity"]].append(float(r["node_coverage"]))
chk("coverage sev 0.5", mean(by_s["0.5"]), 0.5)
chk("coverage sev 0.75", mean(by_s["0.75"]), 0.25)
chk("rows below coverage_floor 0.6", sum(float(r["node_coverage"]) < 0.6 for r in d), 60)
chk("max isolated rate", max(float(r["isolated_node_rate"]) for r in d), 0.4726, 0.0005)

# ---- Phase 4
c = rd("coverage_floor_eval")
chk("phase4 rows", len(c), 1944)
g4 = [r for r in c if r["method"] == "diagnostic_gate"]
chk("gate hybrid 324", sum(r["policy_chosen"] == "hybrid" for r in g4), 324)
chk("gate lexical_only 324", sum(r["policy_chosen"] == "lexical_only" for r in g4), 324)
pol = defaultdict(set)
for r in g4:
    pol[r["severity"]].add(r["policy_chosen"])
chk("policy by severity", {k: sorted(v) for k, v in sorted(pol.items())},
    {"0.0": ["hybrid"], "0.25": ["hybrid"], "0.5": ["lexical_only"], "0.75": ["lexical_only"]})
for sev, want in (("0.0", 0.0), ("0.25", 0.377), ("0.5", 0.593), ("0.75", 0.815)):
    rs = [r for r in c if r["method"] == "bm25" and r["severity"] == sev]
    chk(f"gold hidden fraction sev {sev}", mean([r["any_gold_hidden"] == "True" for r in rs]), want, 0.001)
for sev, n, wants in (("0.5", 66, {"bm25": 0.364, "diagnostic_gate": 0.364, "fixed_hybrid": 0.394}),
                      ("0.75", 30, {"bm25": 0.433, "diagnostic_gate": 0.433, "fixed_hybrid": 0.400})):
    for m, want in wants.items():
        rs = [r for r in c if r["method"] == m and r["severity"] == sev and r["any_gold_hidden"] == "False"]
        chk(f"visible rows {m} sev {sev}", len(rs), n)
        chk(f"hit@5 {m} sev {sev}", mean([float(r["hit_at_5"]) for r in rs]), want)
        by = defaultdict(list)
        for r in rs:
            by[r["repo"]].append(float(r["hit_at_5"]))
        chk_lo, chk_hi = boot(by)
        checks.append({"claim": f"CI {m} sev {sev} (recomputed; manuscript interval from the run's own bootstrap)",
                       "recomputed": [round(chk_lo, 3), round(chk_hi, 3)], "manuscript": "see paper", "pass": None})

# ---- Phase 5
w = rd("weighted_gate_eval")
chk("phase5 rows", len(w), 2592)
wg = [r for r in w if r["method"] == "weighted_gate"]
chk("weighted rows", len(wg), 648)
lw = defaultdict(list)
for r in wg:
    lw[r["severity"]].append(float(r["lexical_weight"]))
checks.append({"claim": "weighted mean lexical weight sev0 / sev0.75", "recomputed":
               [round(mean(lw["0.0"]), 3), round(mean(lw["0.75"]), 3)], "manuscript": "0.50 -> 0.875", "pass": None})
chk("weighted abstains", sum(r["policy_chosen"] == "abstain" for r in wg), 0)
dg = {(r["task_id"], r["severity"], r["seed"]): r["hit_at_5"] for r in w if r["method"] == "diagnostic_gate"}
for sev in ("0.0", "0.5", "0.75"):
    chk(f"weighted ties gate row-for-row sev {sev}",
        sum(dg[(r["task_id"], r["severity"], r["seed"])] != r["hit_at_5"] for r in wg if r["severity"] == sev), 0)
def vis(m, sev):
    return [float(r["hit_at_5"]) for r in w if r["method"] == m and r["severity"] == sev and r["any_gold_hidden"] == "False"]
chk("sev0.25 weighted n", len(vis("weighted_gate", "0.25")), 101)
chk("sev0.25 weighted hit@5", mean(vis("weighted_gate", "0.25")), 0.396)
chk("sev0.25 gate hit@5", mean(vis("diagnostic_gate", "0.25")), 0.426)
chk("sev0.25 fixed_hybrid hit@5", mean(vis("fixed_hybrid", "0.25")), 0.426)
chk("sev0.25 bm25 hit@5", mean(vis("bm25", "0.25")), 0.376)

# ---- stale_rewire
s = rd("stale_rewire_eval")
chk("stale_rewire rows", len(s), 3240)
for m in ("bm25", "fixed_hybrid", "diagnostic_gate"):
    for sev in ("0.0", "0.25", "0.5", "0.75"):
        v = [float(r["hit_at_5"]) for r in s if r["method"] == m and r["severity"] == sev]
        chk(f"stale_rewire {m} sev {sev} = 0.333", mean(v), 0.333)
chk("stale_rewire gate hybrid", sum(r["policy_chosen"] == "hybrid" for r in s if r["method"] == "diagnostic_gate"), 648)
for m, sv, want in (("graph_expansion", "0.0", 0.296), ("graph_expansion", "0.75", 0.278),
                    ("repomap", "0.0", 0.278), ("repomap", "0.75", 0.284)):
    v = [float(r["hit_at_5"]) for r in s if r["method"] == m and r["severity"] == sv]
    chk(f"stale_rewire {m} sev {sv}", mean(v), want)

out = {"n_checks": len(checks), "n_pass": sum(c["pass"] is True for c in checks),
       "n_fail": sum(c["pass"] is False for c in checks), "checks": checks}
(R / "analysis/phase_audit.json").write_text(json.dumps(out, indent=1))
for c in checks:
    print("PASS" if c["pass"] else ("INFO" if c["pass"] is None else "FAIL"), c["claim"], c["recomputed"], "|", c["manuscript"])
print(out["n_pass"], "pass", out["n_fail"], "fail")
