# Retrieval-method audit (Checkpoint 2)

Source: `src/gemma_research/evidence/retrieve.py`, `src/gemma_research/metrics/scoring.py`, run scripts under `experiments/`. Tags: **V** verified by reading code or recomputation, **U** unresolved.

## Methods

| Method | Specification | Notes |
|---|---|---|
| `bm25` | Custom BM25, k1 = 1.5, b = 0.75, over node text; ties by `node_id` | **V** |
| `graph_expansion` | Anchors = top 3 BM25 nodes with positive score; expand one hop; score 1/(1+distance), unreached nodes 1/3 | **V** Nodes outside anchors and neighbours tie, broken alphabetically by `node_id`, which is arbitrary but deterministic. Scores real nodes only. |
| `fixed_hybrid` | 0.5 × normalised BM25 + 0.5 × normalised graph score | **V** |
| `repomap` | Personalised PageRank (α = 0.85) seeded by BM25 anchors | **V** The project's own reimplementation of the idea, not the original tool; the code comment says so. Has the dangling-pseudo-node defect (see `OPERATOR_AUDIT.md`); its effect on hit@5 was bounded from stored metrics only (small, indistinguishable from noise); rankings unstored. Not a clean baseline under `stale_symbol_refs`. |
| `DiagnosticGate` | See below | **V** |
| `WeightedDiagnosticGate` | Lexical weight = 1 − 0.5 × min(coverage, 1 − isolated_rate); same abstain rule | **V** Equals `fixed_hybrid` on a healthy graph, `bm25` on a fully degraded one. Run only on node omission (648 rows). |

## `DiagnosticGate`
Rule: abstain if `anchor_confidence` < 0.1; otherwise `hybrid` if `node_coverage` ≥ 0.6 and `isolated_node_rate` ≤ 0.5, else `lexical_only`. Thresholds (0.6, 0.5, 0.1) date from commit `1090b43` (2026-10-16), before any holdout run, and are unchanged.

Findings:
1. **V — oracle-like input.** Runners set `reference_node_count` to the healthy graph's node count for the same snapshot. Under node omission, coverage therefore equals 1 − severity exactly. A deployed gate would need a prior snapshot or estimate. State as a limitation.
2. **V — edge-only corruption cannot trigger fallback.** Coverage and anchor confidence are unaffected by edge operators, and `isolated_node_rate` never exceeded 0.423 (ceiling 0.5). The gate is `fixed_hybrid` by construction on every edge-only condition: pilot 1,620 of 1,620, stale rewire 648 of 648, holdout 855 of 855 gate rows. This is a consequence of the design and thresholds, not an empirical finding that the gate "matches" the hybrid.
3. **V — abstain never fires** in any result set. The branch is unit-tested but unexercised by data.
4. **V — decisions under node omission:** `hybrid` at severity 0.0 and 0.25, `lexical_only` at 0.5 and 0.75 (162 rows each). Weighted-gate run: 324 `hybrid`, 324 `lexical_only`.
5. **U** Threshold sensitivity was not studied (no sweeps permitted); 0.6/0.5/0.1 were fixed a priori and were not tuned on held-out data.
6. Cost: one BM25 pass plus one adjacency pass.

## Scoring and fairness (V)
- `hit_at_k` takes the top-k ids and does not filter non-node ids.
- All methods receive the same `task.query_text` (no hints, no patch text) and the same node pool.
- Coverage-floor scoring conditions on gold being visible (`any_gold_hidden` false).
- Reranker: candidate and leakage rules audited earlier (`RERANKER_VALIDATION.md`, `scripts/audit_reranker.py`, 0 mismatches over 108 calls). Not re-audited this round. The prompt was revised between v1 and v2 and the 15 v1 tasks lie inside the 54 v2 tasks, so v1 and v2 are not independent evidence.

## Tests
67 tests passed at last full run; operator and gate paths are covered (`tests/test_perturb.py`, `tests/test_retrieve.py`). Not covered: `repomap` with dangling ids; gate behaviour on real abstention cases.

## Manuscript consequences
State the oracle `reference_node_count`; state that edge-only corruption never leaves the hybrid branch; do not describe the gate as validated for abstention. All three, and the `repomap` disclosure, are in `REVISED_PAPER.md` (Checkpoint 3).

**Update (2026-10-22):** the `repomap` defect was quantified by the approved post hoc correction run; see the section at the end of `OPERATOR_AUDIT.md`. Rankings are now stored for that run only. A unit test covers `repomap` with dangling ids.
