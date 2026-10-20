"""Framework-validation run for the shared evaluation harness.

IMPORTANT — what this is and is not:
  - This IS a real, executed run of the shared retrieval/perturbation/metrics
    code on a small, hand-built SYNTHETIC fixture (8 toy functions wired
    into a small call graph). Every number it prints and writes to
    `results/framework_validation/` was actually computed by running this
    script; none of it is invented.
  - This is NOT yet a Candidate-A research pilot on real competition or
    Loc-Bench data. Its only purpose is to prove the harness (perturbation
    manifests, baselines, diagnostic gate, metrics, bootstrap CI) works
    end-to-end and is reproducible, before spending effort wiring it to a
    real repository graph. See research/decision_log.md, "Open blockers".

Usage: `python experiments/pilot_a/run_framework_validation.py`
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from gemma_research.data.types import CodeGraph, Edge, LocalizationTask, Node
from gemma_research.evidence.perturb import missing_edges
from gemma_research.evidence.retrieve import (
    DiagnosticGate,
    bm25_rank,
    fixed_hybrid_rank,
    graph_expansion_rank,
)
from gemma_research.metrics.scoring import bootstrap_ci, hit_at_k

ROOT = Path(__file__).resolve().parents[2]


def build_synthetic_fixture() -> tuple[CodeGraph, list[LocalizationTask]]:
    nodes = (
        Node("auth.login", "toy_repo", "function", "login handles user authentication request"),
        Node("auth.logout", "toy_repo", "function", "logout clears the active session"),
        Node("auth.token", "toy_repo", "function", "token issues a signed session token"),
        Node("db.query", "toy_repo", "function", "query executes a parameterised database query"),
        Node("db.connect", "toy_repo", "function", "connect opens a pooled database connection"),
        Node("util.hash", "toy_repo", "function", "hash computes a salted password hash"),
        Node("util.log", "toy_repo", "function", "log writes a structured log line"),
        Node("api.handler", "toy_repo", "function", "handler routes an incoming http request"),
    )
    edges = (
        Edge("api.handler", "auth.login", "calls"),
        Edge("auth.login", "db.query", "calls"),
        Edge("auth.login", "util.hash", "calls"),
        Edge("auth.login", "auth.token", "calls"),
        Edge("auth.logout", "db.query", "calls"),
        Edge("db.query", "db.connect", "calls"),
        Edge("api.handler", "util.log", "imports"),
        Edge("auth.token", "util.log", "imports"),
    )
    graph = CodeGraph(repo="toy_repo", commit="synthetic-0001", nodes=nodes, edges=edges)

    tasks = [
        LocalizationTask("t1", "toy_repo", "user cannot log in, authentication fails", frozenset({"auth.login"})),
        LocalizationTask("t2", "toy_repo", "session token is not issued after login", frozenset({"auth.token"})),
        LocalizationTask("t3", "toy_repo", "database connection pool exhausted under load", frozenset({"db.connect"})),
        LocalizationTask("t4", "toy_repo", "password hash mismatch on login attempt", frozenset({"util.hash"})),
        LocalizationTask("t5", "toy_repo", "logout does not clear session state", frozenset({"auth.logout"})),
    ]
    return graph, tasks


METHODS = {
    "bm25": lambda graph, q: bm25_rank(graph, q),
    "graph_expansion": lambda graph, q: graph_expansion_rank(graph, q),
    "fixed_hybrid": lambda graph, q: fixed_hybrid_rank(graph, q),
}


def run(config_path: Path) -> dict:
    config = yaml.safe_load(config_path.read_text())
    graph, tasks = build_synthetic_fixture()
    reference_node_count = len(graph.nodes)
    gate = DiagnosticGate()

    rows = []
    manifests = []
    for seed in config["seeds"]:
        for severity in config["severities"]:
            corrupted, manifest = missing_edges(graph, severity=severity, seed=seed)
            manifests.append(
                {
                    "seed": seed,
                    "severity": severity,
                    "operator": manifest.operator,
                    "n_removed_edges": len(manifest.removed_edges),
                    "removed_edges": [f"{e.src}->{e.dst}:{e.edge_type}" for e in manifest.removed_edges],
                }
            )
            for task in tasks:
                for method_name, method_fn in METHODS.items():
                    ranking = method_fn(corrupted, task.query_text)
                    rows.append(
                        {
                            "task_id": task.task_id,
                            "method": method_name,
                            "seed": seed,
                            "severity": severity,
                            "hit_at_3": hit_at_k(ranking, task.gold_node_ids, k=3),
                        }
                    )
                gated_ranking, policy, diag = gate.rank(corrupted, task.query_text, reference_node_count)
                rows.append(
                    {
                        "task_id": task.task_id,
                        "method": "diagnostic_gate",
                        "seed": seed,
                        "severity": severity,
                        "hit_at_3": hit_at_k(gated_ranking, task.gold_node_ids, k=3),
                        "policy_chosen": policy,
                        "node_coverage": diag.node_coverage,
                    }
                )
    summary = {}
    for method in list(METHODS) + ["diagnostic_gate"]:
        for severity in config["severities"]:
            scores = [r["hit_at_3"] for r in rows if r["method"] == method and r["severity"] == severity]
            ci = bootstrap_ci(scores, n_resamples=config["bootstrap_resamples"], seed=0)
            summary[f"{method}@severity={severity}"] = {
                "mean_hit_at_3": ci.point_estimate,
                "ci_low": ci.low,
                "ci_high": ci.high,
                "n_observations": len(scores),
            }
    return {"rows": rows, "summary": summary, "manifests": manifests}


if __name__ == "__main__":
    output_dir = ROOT / "results" / "framework_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run(ROOT / "configs" / "evaluation.yaml")
    (output_dir / "raw_rows.json").write_text(json.dumps(result["rows"], indent=2))
    (output_dir / "summary.json").write_text(json.dumps(result["summary"], indent=2))
    (output_dir / "perturbation_manifests.json").write_text(json.dumps(result["manifests"], indent=2))
    print("Framework validation run complete (SYNTHETIC fixture, not real competition data).")
    print(f"Wrote {len(result['rows'])} raw rows and summary to {output_dir}")
    for key, stats in result["summary"].items():
        print(f"  {key}: mean_hit_at_3={stats['mean_hit_at_3']:.3f} "
              f"CI=[{stats['ci_low']:.3f}, {stats['ci_high']:.3f}] n={stats['n_observations']}")
