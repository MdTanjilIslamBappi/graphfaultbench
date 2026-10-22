# Threats to validity (Checkpoint 2)

Tags: **V** verified, **P** potential (plausible, not measured), **U** unresolved (cannot be settled with existing data). Detail in `OPERATOR_AUDIT.md`, `METHOD_AUDIT.md`, `STATISTICAL_AUDIT.md`.

## Construct validity
| Threat | Tag | Note |
|---|---|---|
| Synthetic corruption may not match real graph faults | U | No ground-truth graph and no study of real builder errors. Benchmark measures retrieval-given-graph robustness only. |
| `stale_symbol_refs` ≈ edge deletion for `bm25`, `graph_expansion`, `fixed_hybrid`, gate | V | Identical rankings at 0.25/0.5/0.75; not an independent stressor. |
| `repomap` dangling-pseudo-node defect | V (defect); U (magnitude) | Dangling ids enter PageRank. Pilot `repomap` hit@5 flat (0.278 → 0.284), so effect looks small, but unquantified; also affects holdout. |
| `high_centrality_edges` is a degree-sum proxy and near-deterministic | V | Not betweenness centrality. |
| `stale_rewire` uniform targets, possible self-loops, achieved fraction may be below nominal | V/U | Not measured on real graphs. |
| `isolated_node_rate` counts dangling edges as present | V | Understates damage for that operator (0.122 vs 0.36 at 0.75). |
| `repomap` is a reimplementation, not the original tool | V | Conclusions about "repo-map" methods do not transfer to the original. |

## Internal validity
| Threat | Tag | Note |
|---|---|---|
| Gate uses healthy node count (oracle-like) | V | Coverage under node omission equals 1 − severity exactly. |
| Gate equals `fixed_hybrid` by construction on edge-only corruption | V | Isolation rate never above 0.423 against a 0.5 ceiling. |
| Abstain branch never exercised | V | Untested on data. |
| Thresholds not swept | V | Fixed a priori; sensitivity unknown. |
| Seed non-independence | V | Healthy graph identical across seeds; only 56 of 2,430 corrupted cells vary. Effective sample 540 pairs per policy. |
| Healthy-set equality claim | V | Equal count (18), unequal sets (one task each way). |
| Reranker prompt revised between v1 and v2; v1 tasks are a subset of v2 | V | v1 and v2 not independent; gain small (see statistics). |
| Tie-breaking by `node_id` | V | Deterministic but arbitrary for tied scores. |

## External validity
| Threat | Tag | Note |
|---|---|---|
| Six repositories, Python only, uneven (18, 11, 11, 7, 5, 2 tasks) | V | One repository (dask) can set the sign of a difference. |
| Loc-Bench V1 tasks only; licence unstated | V | Not redistributed. |
| Holdout: nine conditions, one seed, 95 tasks; 33 tasks (yt-dlp 27, moto 6) at floor for both methods | V | Limited discrimination. |
| Gemma 4 only, 54 tasks × 2 severities = 108 calls | V | No other models. |

## Holdout blinding and chronology
- V Pre-registration `docs/HOLDOUT_PREREGISTRATION.md` committed as `f337085`, 2026-10-22 11:14:40 +0600, with the holdout configuration files. Raw results first committed in `27506a9`, 2026-10-22 19:31:42 +0600. Per-run timestamps are not stored.
- V Gate thresholds (commit `1090b43`, 2026-10-16) predate every holdout run.
- V Holdout repositories and tasks do not overlap earlier results.
- V The holdout was **not blind** in the strict sense. Repo-cache directories for `sympy`, `moto` and `matplotlib` were created 2026-10-20 20:59–21:01 during pilot repository widening; commit `4fc39b2` records graph-size smoke tests on six candidates and the swap-out of `sympy` for size.
- U Whether any retrieval was run on those candidates then, and how far `moto` and `matplotlib` were inspected, is not recorded. No account may be reconstructed from memory.
- Wording to use: "pre-registered before holdout execution; the author had previously inspected graph sizes for some candidate repositories; no earlier retrieval results exist for the holdout tasks."

## Statistical-conclusion validity
| Threat | Tag |
|---|---|
| Six-cluster bootstrap: discrete, coarse, coverage unreliable | V/I |
| MC noise up to ~0.02 in stored CIs; exact enumeration changes CIs by ≤ 0.016 | V |
| Django alone drives the holdout healthy difference (two tasks); exact lower bound is 0.000 with 33.5% of draws at zero | V |
| No equivalence test; "no difference detected" only | V |
| No multiplicity adjustment; pilot analyses exploratory | V |
| Leave-one-out: pilot healthy difference changes sign with dask (−0.028) or prefect (+0.023) | V |

## Reproducibility
- V Seeds, configs, manifests (sha256) and run scripts are committed; 67 tests passed at last full run.
- V Stored CIs reproduce exactly from stored code (max difference 0.0).
- U Graph-builder accuracy and unresolved-call ratios have not been recomputed.
- P Dependence on pinned third-party snapshots staying available.

## Checkpoint 3 updates (2026-10-22)
- `repomap` defect: measured hit@5 changes are small and within the range produced by plain deletion (pilot 0.278→0.284; holdout Django only). Pseudo-node displacement is unobserved because rankings were not stored. Tag stays V (defect) / U (magnitude). Correction run proposed, not executed (the internal correction proposal (withheld from this release)).
- LocAgent author-list discrepancy between the ACL Anthology bibliography ("Tang, Robert") and arXiv ("Xiangru Tang") is unresolved (U); the manuscript uses initials.
- Related-work coverage: bounded search; full texts searched by keyword, not read line by line.
- Interval convention changed to exact enumeration; stored intervals retained as sensitivity analysis.
- `repomap` correction run executed (post hoc, user-approved): pseudo-nodes were in the top-5 in 60–158 of 162 pilot and 74–92 of 95 holdout invocations, but hit@5 changed by at most net two tasks (`OPERATOR_AUDIT.md`). Tag: V (defect and measured effect). The correction was chosen after seeing the original results.
- LocAgent author discrepancy resolved for citation: ACL Anthology metadata used; arXiv lists a different second-author name (recorded in `RELATED_WORK_AUDIT.md`).
