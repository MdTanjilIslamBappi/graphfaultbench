"""Compare original and corrected `repomap` under `stale_symbol_refs` (post hoc correction run).

Reads results/repomap_correction/*/rankings.jsonl and the stored original metrics.csv files.
Checks that the re-run `repomap_original` reproduces the stored hit@5 exactly, then reports
pseudo-node presence in the top-k and per-task changes. Output: results/analysis/repomap_correction.json
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    "pilot": ("results/repomap_correction/pilot_a", ["results/pilot"]),
    "holdout": (
        None,
        [f"results/holdout_{n}" for n in ("django", "matplotlib", "moto", "sqlglot", "sympy", "ytdlp")],
    ),
}


def load_stored(dirs):
    out = {}
    for d in dirs:
        with (ROOT / d / "metrics.csv").open() as f:
            for r in csv.DictReader(f):
                if r["method"] == "repomap" and r["operator"] == "stale_symbol_refs":
                    out[(r["task_id"], float(r["severity"]), int(r["seed"]))] = float(r["hit_at_5"])
    return out


def load_rankings(paths):
    rows = []
    for p in paths:
        with (ROOT / p / "rankings.jsonl").open() as f:
            rows += [json.loads(line) for line in f]
    return rows


def analyse(rows, stored):
    by = defaultdict(dict)
    for r in rows:
        by[(r["task_id"], r["severity"], r["seed"])][r["method"]] = r
    res = {"n_invocations": len(by), "by_severity": {}}
    mism = sum(1 for k, v in by.items() if k in stored and v["repomap_original"]["hit_at_5"] != stored[k])
    res["original_rerun_mismatches_vs_stored"] = mism
    res["missing_from_stored"] = sum(1 for k in by if k not in stored)
    sevs = sorted({k[1] for k in by})
    for s in sevs:
        ks = [k for k in by if k[1] == s]
        o = [by[k]["repomap_original"] for k in ks]
        c = [by[k]["repomap_corrected"] for k in ks]
        res["by_severity"][str(s)] = {
            "n": len(ks),
            "hit5_original": sum(x["hit_at_5"] for x in o) / len(ks),
            "hit5_corrected": sum(x["hit_at_5"] for x in c) / len(ks),
            "mrr_original": sum(x["mrr"] for x in o) / len(ks),
            "mrr_corrected": sum(x["mrr"] for x in c) / len(ks),
            "invocations_with_dangling_in_top5": sum(x["dangling_in_top5"] > 0 for x in o),
            "invocations_with_dangling_in_top10": sum(x["dangling_in_top10"] > 0 for x in o),
            "mean_dangling_in_top5": sum(x["dangling_in_top5"] for x in o) / len(ks),
            "corrected_dangling_in_top10": sum(x["dangling_in_top10"] for x in c),
            "hit5_gained_by_correction": sum(a["hit_at_5"] > b["hit_at_5"] for a, b in zip(c, o)),
            "hit5_lost_by_correction": sum(a["hit_at_5"] < b["hit_at_5"] for a, b in zip(c, o)),
            "top5_set_changed": sum(a["top10"][:5] != b["top10"][:5] for a, b in zip(c, o)),
        }
    return res


if __name__ == "__main__":
    require("analyse_repomap_correction.py", "results/repomap_correction/pilot_a/rankings.jsonl", "results/pilot/metrics.csv")
    out = {}
    pilot_rows = load_rankings([RUNS["pilot"][0]])
    out["pilot"] = analyse(pilot_rows, load_stored(RUNS["pilot"][1]))
    hold = load_rankings(
        [f"results/repomap_correction/holdout_{n}" for n in ("django", "matplotlib", "moto", "sqlglot", "sympy", "ytdlp")]
    )
    out["holdout"] = analyse(hold, load_stored(RUNS["holdout"][1]))
    (ROOT / "results/analysis/repomap_correction.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
