# Novelty assessment — Candidate A (GraphFaultBench), post-pilot

This document assesses what the real pilot (`reports/pilot_results.md`)
actually supports about Candidate A's claimed contribution, separating the
benchmark/harness contribution from the `DiagnosticGate` method
contribution. It supersedes the pre-pilot "preliminary lean" recorded in
`research/decision_log.md` and `STATUS.md`'s Phase 1 entry, which was
evidence-backed from literature review alone and explicitly flagged as
pending this pilot.

## 1. The benchmark/harness contribution

The pilot exercised the full harness end-to-end on real, previously unseen
data: downloading commit-pinned snapshots of three public repositories,
building call/import graphs by static analysis, resolving 47 real
Loc-Bench V1 gold-label rows against those graphs with zero exclusions,
applying three independent corruption operators at three severities, and
scoring five retrieval methods with a clustered bootstrap. No part of this
pipeline required the organiser's Kaggle bundle, fine-tuning, or GPU
access, consistent with the directive's resource constraints.

This supports a defensible claim: **the harness itself — real-data
ingestion, graph construction, leakage-controlled task construction,
corruption operators and clustered-bootstrap evaluation — functions
correctly on real repositories and produces reproducible, auditable
output.** This is the "Best New Resource" framing adopted after Phase 1,
and the pilot is evidence for it, not merely an assertion.

## 2. The `DiagnosticGate` method contribution

This is the part of Candidate A's original pitch that is **not supported**
by the pilot. `reports/pilot_results.md` §6 shows `DiagnosticGate` chose
the `"hybrid"` policy on all 1,200 of its invocations (100%), making it
numerically identical to the much simpler `fixed_hybrid` baseline on every
metric and every corruption condition tested.

The mechanism is traceable directly in
`src/gemma_research/evidence/retrieve.py::compute_diagnostics` and
`DiagnosticGate.choose_policy`, not merely inferred from the output:

- `node_coverage = len(graph.nodes) / reference_node_count`. All three
  corruption operators used in this pilot (`missing_edges`,
  `high_centrality_edges`, `stale_symbol_refs`) remove or redirect edges
  only; none of them changes the node set (confirmed in
  `experiments/pilot_a/run_real_pilot.py`'s inline comment and in the
  operators' own implementations in `src/gemma_research/evidence/perturb.py`).
  `node_coverage` is therefore exactly 1.0 on every row by construction,
  regardless of corruption severity.
- `anchor_confidence = min(1.0, top_bm25_score / 10.0)` depends only on
  node text and the query, both unaffected by edge-only corruption, so it
  is also exactly 1.0 on every row.
- `isolated_node_rate` is the only one of the three diagnostic signals
  that responds to the corruption applied here, rising from a mean of
  0.003 at zero severity to a mean of 0.311 under `missing_edges` at
  severity 0.75. However, the gate's threshold (`isolated_ceiling = 0.5`)
  is never crossed at the severities tested, so `graph_reliable` evaluates
  to `True` on every row and the policy never switches away from
  `"hybrid"`.

**Conclusion: the gate's two coverage-related signals are structurally
insensitive to the class of corruption this pilot studies (edge-only
perturbation), and the one signal that does respond does not reach the
configured switching threshold within the severity range tested.** This
is not a bug in the implementation; it is a mismatch between what the
diagnostic signals measure and what this pilot's corruption operators
perturb, combined with threshold values that were set during development
(per the contingency protocol, never fit on held-out data) without the
benefit of this empirical signal.

This is a genuine negative result for the method contribution as currently
specified, and it is reported as such rather than reframed. It does not,
by itself, invalidate the benchmark contribution (§1), and the directive's
own criteria explicitly treat negative or mixed method results as
acceptable and scientifically valuable.

## 3. What would be needed to make a method-level claim defensible

Not undertaken in this pilot, and listed here only as what the evidence
indicates would be required, not as a promise of a specific future result:

1. A corruption operator that perturbs node-level coverage directly (e.g.
   removing whole files/modules from the graph, rather than only edges),
   which is the condition `node_coverage` was designed to detect.
2. Re-examining the `isolated_ceiling` threshold against the empirical
   distribution now available (mean isolated-node rate up to 0.31 at the
   highest severity and operator tested here), rather than the
   development-time value of 0.5 chosen before any real data existed.
3. Evaluating whether `anchor_confidence`, as currently normalised against
   a fixed constant (`/ 10.0`), is a meaningful signal at all for this
   corpus scale, given it saturated to 1.0 on every single query observed.

None of this is implemented or claimed to work; it is scoped future work,
discussed again in `research/go_no_go.md`.

## 4. Comparison with graph-structural baselines

`graph_expansion` (pure graph-neighbourhood expansion from lexical
anchors) and `repomap` (this project's own PageRank reimplementation of
the idea behind aider's RepoMap, not the original tool) both underperform
`bm25` on `hit_at_1` and are statistically indistinguishable from it on
`hit_at_5` given the available confidence intervals. This is consistent
with, though not strong independent confirmation of, the Phase 1 thesis
that the proposed graph structure (built via heuristic, name-based call
resolution — see `reports/pilot_results.md` §3's unresolved-call counts)
is too noisy on its own to improve over lexical retrieval at this scale,
and that any benefit from graph information requires combining it with
lexical signal rather than relying on it exclusively.
