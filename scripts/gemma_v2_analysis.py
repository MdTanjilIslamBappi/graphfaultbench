"""Pre-registered Gemma v2 comparison (docs/GEMMA_V2_PREREGISTRATION.md). Stdlib only.

Usage: python scripts/gemma_v2_analysis.py -> results/gemma_v2/summary.json
Paired difference in hit@5 (gemma - comparator), repository-clustered bootstrap.
"""
import collections
import json
import random
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parent.parent
require("gemma_v2_analysis.py", "results/gemma_v2/calls.jsonl")
with open(ROOT / "results/gemma_v2/calls.jsonl") as f:
    calls = [json.loads(line) for line in f]
rng = random.Random(20261022)
B = 5000


def boot(by_repo):
    repos = list(by_repo)
    n = sum(len(v) for v in by_repo.values())
    est = sum(sum(v) for v in by_repo.values()) / n
    s = []
    for _ in range(B):
        pick = [by_repo[rng.choice(repos)] for _ in repos]
        s.append(sum(sum(v) for v in pick) / sum(len(v) for v in pick))
    s.sort()
    return est, s[int(.025 * B)], s[int(.975 * B)]


def mean(x):
    return sum(x) / len(x)


out = {"n_calls": len(calls), "n_tasks": len({c["task_id"] for c in calls}), "strata": {}}
for label, sel in (("all", lambda c: True), ("severity_0.0", lambda c: c["severity"] == 0.0),
                   ("severity_0.5", lambda c: c["severity"] == 0.5)):
    cs = [c for c in calls if sel(c)]
    d = {"n": len(cs)}
    for m in ("gemma", "fixed_hybrid", "bm25"):
        d[f"hit5_{m}"] = round(mean([c["hit5"][m] for c in cs]), 4)
        d[f"hit1_{m}"] = round(mean([c["hit1"][m] for c in cs]), 4)
        d[f"mrr_{m}"] = round(mean([c["mrr"][m] for c in cs]), 4)
    for comp in ("fixed_hybrid", "bm25"):
        by = collections.defaultdict(list)
        for c in cs:
            by[c["repo"]].append(c["hit5"]["gemma"] - c["hit5"][comp])
        e, lo, hi = boot(by)
        d[f"paired_hit5_gemma_minus_{comp}"] = {"mean": round(e, 4), "ci95": [round(lo, 4), round(hi, 4)]}
    d["pool_recall_top15"] = round(mean([c["pool_recall"] for c in cs]), 4)
    d["parse_valid_5_of_5"] = sum(c["n_parsed_valid"] == 5 for c in cs)
    d["mean_valid_ids"] = round(mean([c["n_parsed_valid"] for c in cs]), 3)
    d["mean_latency_s"] = round(mean([c["runtime_seconds"] for c in cs]), 2)
    d["mean_prompt_tokens"] = round(mean([c["prompt_tokens"] for c in cs]), 1)
    out["strata"][label] = d
by = collections.defaultdict(list)
for c in calls:
    by[c["repo"]].append(c["hit5"]["gemma"] - c["hit5"]["fixed_hybrid"])
out["per_repo_gemma_minus_fixed_hybrid"] = {r: round(mean(v), 3) for r, v in sorted(by.items())}
(ROOT / "results/gemma_v2/summary.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
