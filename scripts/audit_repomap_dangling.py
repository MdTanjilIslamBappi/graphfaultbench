"""Existing-artifact audit of the `repomap` dangling-pseudo-node defect.

Reads only stored `metrics.csv` files. Reports, for `repomap`, per-task hit@5
changes from the healthy control under each edge operator, so that
`stale_symbol_refs` (pseudo-nodes enter PageRank) can be set beside
`missing_edges` (same fraction of edges simply deleted). Rankings are not
stored, so whether a pseudo-node entered a top-k list cannot be read from
these files; that limit is recorded in the output.
"""

from __future__ import annotations

import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

from _inputs import require

ROOT = Path(__file__).resolve().parents[1]
SETS = ["pilot"] + [f"holdout_{r}" for r in ("django", "sympy", "moto", "matplotlib", "sqlglot", "ytdlp")]
OPS = ("stale_symbol_refs", "missing_edges", "high_centrality_edges", "stale_rewire")


def main() -> None:
    require("audit_repomap_dangling.py", *[f"results/{n}/metrics.csv" for n in SETS])
    out: dict[str, object] = {
        "limit": "metrics.csv stores no rankings; pseudo-node presence in top-k is not observable here.",
        "sets": {},
    }
    for name in SETS:
        with open(ROOT / "results" / name / "metrics.csv") as fh:
            rows = [r for r in csv.DictReader(fh) if r["method"] == "repomap"]

        def per_task(op: str, sev: float | None = None, rows: list[dict[str, str]] = rows) -> tuple[dict[str, float], float]:
            acc: dict[str, list[float]] = defaultdict(list)
            edges: list[int] = []
            for r in rows:
                if r["operator"] == op and (sev is None or float(r["severity"]) == sev):
                    acc[r["task_id"]].append(float(r["hit_at_5"]))
                    edges.append(int(r["n_graph_edges"]))
            return {k: st.mean(v) for k, v in acc.items()}, (st.mean(edges) if edges else 0.0)

        healthy, _ = per_task("healthy_control")
        entry: dict[str, object] = {}
        for op in OPS:
            for sev in sorted({float(r["severity"]) for r in rows if r["operator"] == op}):
                c, mean_edges = per_task(op, sev)
                ks = [k for k in c if k in healthy]
                entry[f"{op}@{sev}"] = {
                    "n_tasks": len(ks),
                    "healthy_hit5": round(st.mean(healthy[k] for k in ks), 4),
                    "corrupted_hit5": round(st.mean(c[k] for k in ks), 4),
                    "tasks_lost": sum(healthy[k] > c[k] for k in ks),
                    "tasks_gained": sum(c[k] > healthy[k] for k in ks),
                    "mean_graph_edges": round(mean_edges),
                    "affected_edges_upper_bound_pseudo_nodes": round(mean_edges * sev) if op == "stale_symbol_refs" else None,
                }
        out["sets"][name] = entry  # type: ignore[index]
    dest = ROOT / "results" / "analysis" / "repomap_dangling_impact.json"
    dest.write_text(json.dumps(out, indent=2))
    print(dest)


if __name__ == "__main__":
    main()
