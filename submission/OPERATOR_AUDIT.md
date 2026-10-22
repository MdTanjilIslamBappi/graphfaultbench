# Corruption-operator audit (Checkpoint 2)

Source: `src/gemma_research/evidence/perturb.py`, `gold_visibility.py`; tests in `tests/test_perturb.py`; deterministic checks on synthetic graphs; real-data statistics from `results/`. Tags: **V** verified, **C** contradicts a manuscript statement, **U** unresolved.

## Scope of what is measured
The benchmark measures retrieval-given-graph robustness: how rankings change when a *correct* graph is synthetically degraded. It does not measure graph-construction robustness, and no ground-truth call graph exists to calibrate the graph builder's accuracy (**U**). Correspondence between any operator and real-world graph faults is unvalidated (**U**); `stale_rewire`'s docstring already says it is a synthetic proxy.

## Common properties (V)
- Operators never touch node text or gold labels; only edges (or node visibility for `node_omission`).
- All are deterministic given (graph, severity, seed). Sub-seeds use SHA-256 `_stable_seed`, except `node_omission` and `stale_rewire`, which use `random.Random(seed)` directly (deterministic, but a different seeding convention).
- Severity is a fraction of edges (nodes for `node_omission`) via `round(n × severity)`.
- Severity 0 is a no-op (tested).

## Per operator

| Operator | Mechanism | Findings |
|---|---|---|
| `missing_edges` | Remove a fraction of edges, stratified by edge type, seeded shuffle | **V** Behaves as documented. Seed-sensitive. |
| `high_centrality_edges` | Remove the top fraction of edges ranked by deg(src)+deg(dst) | **V** The seed only breaks ties, so the operator is almost deterministic, consistent with few seed-sensitive cells. **C** "Preferential removal from high-degree nodes" should read "removal of the edges with the highest endpoint-degree sum". Degree sum is a proxy, not betweenness centrality. |
| `stale_rewire` | Redirect a fraction of edge targets to a random same-kind node anywhere in the repository | **V** Can create self-loops (1 in the synthetic test). If no same-kind alternative exists the edge is kept, so the achieved fraction can fall below nominal (15 of 15 achieved in the synthetic test; not measured on real graphs, **U**). Targets are uniform, not locality-preserving, which is harsher than typical staleness. |
| `stale_symbol_refs` | Replace an edge's `dst` with `__DANGLING__:<dst>` | See below. |
| `node_omission` | Hide a uniform random fraction of nodes and incident edges; gold not protected | **V** P(gold hidden) equals severity. The run script builds a fresh `BM25Index` on the reduced pool, so hidden nodes are not retrievable and BM25 statistics (IDF, mean length) change. Gold visibility is a property of the condition and is reported separately (coverage-floor scoring uses gold-visible rows). |

## `stale_symbol_refs`: construct validity (V)
- Edge count is unchanged, and `isolated_node_rate` counts dangling edges as present: 0.122 at severity 0.75, against 0.36 for `missing_edges`.
- **V** For `bm25`, `graph_expansion`, `fixed_hybrid` (and hence the gate), the resulting rankings are *identical* to deleting the same edges. Checked at severities 0.25, 0.5 and 0.75. For these methods it is not a distinct stressor; it is `missing_edges` with the same edge sample.
- **V — implementation defect.** `repomap_rank` builds a NetworkX graph from all edge endpoints, so `__DANGLING__:` pseudo-nodes enter the PageRank ranking. In a synthetic test, 6 of the top 10 were dangling ids. They can never be gold and so displace real candidates. `graph_expansion_rank` scores only `graph.nodes` and is unaffected.
- **Measured from stored metrics (`scripts/audit_repomap_dangling.py`, `results/analysis/repomap_dangling_impact.json`).** Pilot `repomap` hit@5: 0.278 healthy; 0.284 at all three `stale_symbol_refs` severities; per-task flips 1 lost / 2 gained (0.25, 0.50) and 1 / 1 (0.75). Plain deletion (`missing_edges`) gives similar flips (1–3 tasks each way; hit@5 0.284–0.290), so the change is within the range produced by edge removal alone. Mean pilot graph has 41,235 edges, so up to about 10,309 / 20,618 / 30,926 edges are redirected. Holdout: only Django changes (1 lost / 1 gained at both severities; hit@5 0.314 unchanged); sympy, moto, matplotlib, sqlglot and yt-dlp show no change.
- **Inference, not measurement.** Rankings were not stored, so the number of pseudo-nodes in any top-k cannot be observed. The data show no evidence of a material effect on hit@5 but cannot separate the defect from noise or exclude per-task displacement. `repomap` results under `stale_symbol_refs` must not be presented as a clean baseline. See the internal correction proposal (withheld from this release) (not executed).
- No test covers `repomap` with dangling ids.
- **Not fixed.** Fixing would change reported results; this needs the user's decision. Recommended: disclose in the manuscript and, if approved, re-run `repomap` only with pseudo-nodes excluded.

## Manuscript consequences
1. Describe `high_centrality_edges` as degree-ranked removal.
2. State that `stale_symbol_refs` equals edge deletion for all methods except `repomap`; do not present it as an independent corruption class for the hybrid.
3. State the `repomap` defect, the measured hit@5 changes, and that the pseudo-node count in rankings is unobserved. (Done in `REVISED_PAPER.md`.)
4. Note possible self-loops and under-achieved rewiring in `stale_rewire`.
5. Keep the measurement-scope sentence above.

## Post hoc `repomap` correction run (2026-10-22, user-approved)
Fix: `exclude_unknown_nodes=True` drops edge endpoints that are not graph nodes before PageRank; no other ranking logic changed. Run on `stale_symbol_refs` only: pilot 54 tasks × 3 severities × 3 seeds = 486, holdout 95 × 2 = 190 invocations per variant. The uncorrected variant reproduced the stored hit@5 in all 676 invocations (0 mismatches). Originals are untouched.

| Set | Severity | Invocations with ≥1 pseudo-node in top-5 | Mean pseudo-nodes in top-5 | hit@5 original → corrected | Tasks gained / lost |
|---|---|---|---|---|---|
| Pilot | 0.25 | 60/162 | 0.42 | 0.284 → 0.290 | 1 / 0 |
| Pilot | 0.50 | 130/162 | 1.06 | 0.284 → 0.290 | 1 / 0 |
| Pilot | 0.75 | 158/162 | 1.67 | 0.284 → 0.296 | 3 / 1 |
| Holdout | 0.50 | 74/95 | 1.11 | 0.200 → 0.200 | 1 / 1 |
| Holdout | 0.75 | 92/95 | 1.65 | 0.200 → 0.211 | 1 / 0 |

Measured: pseudo-nodes occupy top-5 places in a large share of invocations (rising with severity), so the defect was substantial for rankings, yet hit@5 changes by at most 3 tasks net 2. Inference: the baseline's conclusions do not change because it scores below `bm25` on healthy graphs (15/54 v 18/54; the variants coincide there) and no headline claim depends on it under this operator. Corrected `repomap` should be read as the intended baseline; the original numbers stay in the results files as the as-run record. MRR at pilot 0.25 fell (0.241 → 0.226), the only metric that moved appreciably; investigated below.

### MRR at pilot severity 0.25 (investigated, no new run; `scripts/analyse_repomap_mrr.py`, `results/analysis/repomap_mrr_audit.json`)
MRR here is the reciprocal of the gold node's rank in the *full* ranking. Only the top 10 are stored, but the rank is recoverable as 1/MRR. Checks over all stored rows (pilot 972, holdout 380): 1/MRR is an integer rank everywhere, hit@5 equals (rank ≤ 5) everywhere, stored `dangling_in_top5` equals the count recomputed from the top-10 list, every cell has 162 (pilot) or 95 (holdout) paired invocations, and the uncorrected MRR equals the stored `metrics.csv` value in all 486 pilot invocations. No inconsistency was found.

| Pilot severity | MRR original | MRR corrected | Difference | Invocations with changed gold rank | Gold rank 1 in original |
|---|---|---|---|---|---|
| 0.25 | 0.2409 | 0.2261 | −0.0148 | 121/162 | 32 |
| 0.50 | 0.2377 | 0.2392 | +0.0015 | 120/162 | 33 |
| 0.75 | 0.2386 | 0.2392 | +0.0006 | 123/162 | 34 |
| Holdout 0.50 | 0.1427 | 0.1429 | +0.0002 | 78/95 | 9 |
| Holdout 0.75 | 0.1471 | 0.1476 | +0.0005 | 80/95 | 10 |

Decomposition at 0.25: of the −0.0148, −0.0175 comes from the 32 invocations whose gold node was ranked first in the original (13 invocations of 162 fell in total, 108 rose; the two largest falls are rank 1 to rank 3: one dask task at seed 1 and one scipy task at seed 2), partly offset by +0.0035 from gold nodes deeper than rank 10. Both rank-1 to rank-3 cases have no pseudo-node in the top 5 in either variant.

Interpretation (mechanism read from the code, size measured): `repomap_rank` passes `dangling=personalization`, so every pseudo-node is a sink whose mass returns to the BM25 anchors. Pseudo-nodes therefore change real-node scores even when none of them reaches the top 5, which also changes the order of nearly tied top-ranked nodes. Because reciprocal rank is steeply non-linear (1 → 1/3), a few top-rank swaps dominate the mean. The corrected 0.25 value (0.2261) lies within the `missing_edges` range (0.2282 to 0.2380), consistent with the corrected variant behaving like plain deletion; the original 0.2409 was the highest of any `repomap` condition apart from `high_centrality_edges` at 0.5 (0.2549). The healthy-graph MRR is 0.2136. The 0.25 drop is within the variation visible between operators and severities, is not a significance claim, and does not alter hit@5, the paper's primary metric. The gold rank changed in about three quarters of invocations, so rank positions (not just the top 5 set) are sensitive to the defect.
