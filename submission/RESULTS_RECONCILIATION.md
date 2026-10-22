# Results reconciliation: tasks, rows, denominators (2026-10-22)

All counts recomputed from `results/*/metrics.csv` and `results/gemma_v2/calls.jsonl` (stdlib scripts: `scripts/audit_phases.py`, `scripts/audit_holdout_ci.py`, `scripts/audit_reranker.py`). No duplicate (task, operator, severity, seed, method) keys exist in any file.

## 1. Task units

| Unit | Count | Notes |
|---|---|---|
| Loc-Bench attempts / resolved / excluded | 65 / 64 / 1 | one task excluded (gold could not be resolved) |
| Resolved tasks, development / evaluation | 10 / 54 | hash-based split, `dev_fraction: 0.2` |
| Distinct (repo, commit) snapshots | 58 (48 hold evaluation tasks) | each task maps to exactly one commit; at most 3 tasks share a commit |
| Evaluation tasks per repository | dask 18, mypy 11, prefect 11, scipy 7, aiohttp 5, numpy 2 | **very unequal cluster sizes**: numpy has two tasks, so repository-clustered intervals rest on small, uneven clusters |
| Holdout tasks | 95 (none excluded) | sqlglot, yt-dlp, Django, moto, sympy, matplotlib; no repository or task-ID overlap with pilot |
| Gemma tasks | 54 (the pilot evaluation tasks) | 15 of them also appear in the earlier v1 demo |

## 2. Row accounting

A "row" is one (task, operator, severity, seed, policy) evaluation. Rows are **not** all independent: see section 3.

| Result set | Rows | Decomposition |
|---|---|---|
| Pilot (`results/pilot`) | 8,100 | 5 policies x 1,620; 1,620 = 54 tasks x 10 conditions x 3 seeds; conditions = healthy + 3 operators x 3 severities (0.25, 0.5, 0.75) |
| Pilot gate invocations | 1,620 | 162 healthy (54 x 3 seeds) + 1,458 corrupted |
| Node omission, evaluation (`coverage_floor_eval`) | 1,944 | 3 policies (bm25, fixed_hybrid, gate) x 648; 648 = 54 x 4 severities x 3 seeds (healthy 486 + corrupted 1,458 in total) |
| Weighted gate run (`weighted_gate_eval`) | 2,592 | 4 policies x 648; **648 `weighted_gate` rows** = 54 x 4 x 3 |
| `stale_rewire` (`stale_rewire_eval`) | 3,240 | 5 policies x 648; 648 = 54 x 4 severities x 3 seeds (its healthy rows are repeated: 810 healthy = 5 x 162) |
| Holdout | 4,275 | 5 policies x 855; 855 = 95 tasks x 9 conditions; conditions = 4 operators x {0.5, 0.75} + 1 shared healthy; 1 seed |
| Holdout gate rows | 855 | as above |
| Gemma v2 | 108 calls | 54 tasks x 2 severities (0.0, 0.5), `missing_edges`, seed 1 |

## 3. What a row is not

- **Seeds are replicates of the corruption draw only.** In the pilot the healthy graph is identical across the three seeds (0 of 270 task-policy cells vary), so the 162 healthy gate rows are 54 distinct evaluations, each triplicated. For corrupted conditions, only 56 of 2,430 task-condition-policy cells differ in hit@5 across seeds (fixed_hybrid 18, gate 18, repomap 13, graph_expansion 7; bm25 none, as it ignores the graph). The pilot's 8,100 rows therefore carry far fewer than 8,100 independent observations; the unique task-condition pairs number 540 per policy.
- "Gate equals fixed hybrid on 1,620 rows" counts those seed replicates; the unique-pair statement is 540 of 540.
- Reported means over rows (0.333, 0.338, 0.338) weight every task-condition equally across seeds; they are descriptive.

## 4. Metric reconciliation

All values reproduced by the scripts named above. Cluster intervals are 95% percentile intervals with the repository as resampling unit.

| Quantity | Value | Status |
|---|---|---|
| Pilot healthy hit@5 (bm25 / fixed_hybrid / graph_expansion / repomap) | 18 / 18 / 16 / 15 of 54 | reproduced |
| Holdout healthy hit@5 (bm25 / fixed_hybrid) | 21 / 23 of 95; +0.021; CI [0.000, 0.0455] | reproduced, and by exact enumeration of all 6^6 resamples |
| Holdout gate = fixed_hybrid | 855 / 855 rows | reproduced |
| Gemma hit@5 (reranked / fixed_hybrid) | 43/108 / 36/108 | reproduced |
| Gemma gain | 7 calls in 6 tasks, none lost | reproduced |
| Gemma output validity | 83 five-valid-id calls, 25 with four | reproduced |
| Gemma gold-in-pool | 45/108 (0.417) | reproduced; a property of this pool (top 15 of `fixed_hybrid`), not a general ceiling |
| Gemma paired CI | [0.036, 0.097] | reproduced |
| Phase 3-5 | 94/94 audit checks | reproduced; CI endpoints in the paper match the stored `summary.json` but my independent bootstrap differs by up to ~0.03 |

## 5. Discrepancies found and resolved (this audit)

1. Pilot "1,620 invocations under three edge-only operators": 1,458 corrupted + 162 healthy. Corrected.
2. `isolated_node_rate` range 0.003 to 0.360 applied to `missing_edges` only. Corrected.
3. The paper did not explain the 4,275 / 855 holdout arithmetic or that the holdout has five policies. Corrected.
4. Seed replication was not disclosed as non-independent. Added here; to be carried into the paper's validity section.
5. Cluster-size imbalance (numpy 2 tasks, dask 18) was not disclosed. Added here.

## 6. Unresolved

- Graph-builder accuracy and unresolved-call ratios: no ground truth; not recomputed.
- Informal prior inspection of the holdout repositories before registration: unrecorded.
- Whether the stored CI procedure's weighting matches the paper text exactly: endpoints reproduced only to ~0.03.

## 6. Checkpoint 3 additions (2026-10-22)

- **Healthy-set equality.** The pilot bm25 and fixed_hybrid both solve 18 of 54 tasks, but not the same 18: fixed_hybrid alone solves one dask task, bm25 alone one prefect task. Gate solved set equals fixed_hybrid's. The earlier wording "exactly the same 18" is withdrawn.
- **Unit of analysis.** 540 unique task-condition pairs per policy (54 tasks × 10 conditions); the 1,620 invocations include seed repeats (162 healthy rows are 54 evaluations ×3).
- **Interval convention.** Exact enumeration is primary; stored intervals are a sensitivity analysis (`results/analysis/exact_ci_table.json`). Changed values: pilot healthy difference [−0.056, 0.041] → [−0.057, 0.041]; Gemma gain [0.036, 0.097] → [0.035, 0.097]; holdout [0.000, 0.0455] unchanged (reported [0.000, 0.045]).
- **`repomap` under `stale_symbol_refs`.** Pilot hit@5 0.278 → 0.284 at all severities; holdout Django only (1 lost / 1 gained). Pseudo-node presence in rankings is not observable. Not a clean baseline. No re-run (proposal only).
- No raw output, threshold, prompt or split was changed.

## 7. `repomap` correction run (post hoc, 2026-10-22)
Supersedes the "no re-run" statement in §6. 486 pilot + 190 holdout invocations per variant; uncorrected variant matched stored hit@5 in all of them. Corrected hit@5: pilot 0.290, 0.290, 0.296 (original 0.284); holdout 0.200, 0.211 (original 0.200). Original result files are unchanged; the corrected numbers are in `results/repomap_correction/` and `results/analysis/repomap_correction.json`.
