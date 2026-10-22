# Statistical audit (Checkpoint 2)

Date: 2026-10-22. Status tags: **V** verified by recomputation, **I** interpretation, **U** unresolved.
Sources: `scripts/audit_bootstrap.py` → `results/analysis/bootstrap_audit.json`; `scripts/audit_holdout_ci.py` → `results/analysis/holdout_exact_bootstrap.json`; `submission/RESULTS_RECONCILIATION.md`.

## 1. Bootstrap discrepancy

Two implementations existed. They do not estimate the same interval, and both are Monte Carlo (MC) over only six clusters.

| | Stored CIs | Paired analysis |
|---|---|---|
| Code | `src/gemma_research/metrics/scoring.py:bootstrap_ci_clustered` | `scripts/paired_analysis.py` |
| Quantity | marginal mean per method and condition | paired difference between methods |
| Resampling unit | repository (6), with replacement | repository (6), with replacement |
| Weighting | row-pooled (weight ∝ task × seed rows in the repository) | task-level difference, pooled |
| Replicates / seed | 2,000 / `Random(0)` | 5,000 / 20261022 |
| Upper index | `int(.975n)-1` | `int(.975B)` (one position higher) |

**V — controlled comparison on identical inputs** (exact enumeration of all 6^6 = 46,656 repository draws, as the reference):

| Check | Max abs. difference |
|---|---|
| Stored JSON vs re-running the stored function | 0.0 (exact reproduction) |
| Stored vs exact (pilot / coverage-floor / stale-rewire) | 0.0157 / 0.0085 / 0.0024 |
| MC5000 re-implementation vs exact (same three sets) | 0.006 / 0.0232 / 0.0034 |
| Paired intervals vs exact, pilot (30 intervals) | 0.0047 |
| Paired intervals vs exact, holdout (27 intervals) | 0.0007 |

**Root cause (V/I).** Not a bug and not a different estimand. With six clusters the bootstrap distribution is discrete and lumpy, so a 2,000-replicate MC percentile moves by up to about 0.02 between seeds, and the percentile-index convention adds a further one-position shift. The "about 0.03" noted earlier was this noise. Coverage-floor scoring uses gold-visible rows only, so cluster weights differ there (101 visible rows at severity 0.25).

**Decision for Checkpoint 3.** Report exact enumerated intervals as primary, state that they replace the MC values, and keep the stored values in a sensitivity table. Table CIs change by at most 0.016; each change is traceable to this audit and not a copy-editing choice.

## 2. Six clusters

- **I** Six repositories give a coarse bootstrap. Percentile intervals from six clusters have unreliable coverage; the intervals are descriptive, not calibrated 95% statements. Say so.
- Evaluation tasks per repository: dask 18, mypy 11, prefect 11, scipy 7, aiohttp 5, numpy 2. Row-pooled weighting gives dask nine times numpy's weight.
- Holdout: Django contributes the only non-zero healthy difference (two tasks). Exact healthy-difference CI [0.000, 0.0455]; 33.5% of draws equal exactly zero and none is negative, so the lower bound 0.000 is a property of the resampling, not strong evidence of a gain.

### Leave-one-repository-out (V)
- Pilot healthy `fixed_hybrid` − `bm25`: dask +1 task, prefect −1, all others 0. Excluding dask gives −0.028; excluding prefect gives +0.023. The sign of the headline difference is therefore carried by two tasks in two repositories.
- Gemma reranker gain stays positive in every leave-one-out run (0.053–0.071). Per-repository gain (sum over calls): mypy 1/22, dask 2/36, prefect 2/22, scipy 2/14, numpy 0/4, aiohttp 0/10. The gain is small, spread over four repositories, and absent in two.

## 3. Repeated observations (seeds)

- **V** The healthy graph is identical across seeds: 0 of 270 task-policy cells vary. The 162 healthy gate rows are 54 evaluations triplicated.
- **V** Only 56 of 2,430 corrupted task-condition-policy cells change hit@5 across seeds (`fixed_hybrid` 18, gate 18, `repomap` 13, `graph_expansion` 7, `bm25` 0).
- **I** The effective sample is 540 unique task-condition pairs per policy; 1,620 is an invocation count. "Gate equals `fixed_hybrid`" is 540 of 540 unique pairs. Seeds must not be described as independent replication. Standard errors that treat 1,620 rows as independent would be too small; the cluster bootstrap avoids this but only at repository level.
- Holdout uses one seed: 95 tasks × 9 conditions = 855 gate rows, all identical to `fixed_hybrid`.

## 4. Healthy-set result

**V — corrected claim.** `fixed_hybrid` and `bm25` each solve 18 of 54 healthy tasks, but not the same 18: `fixed_hybrid` alone solves one dask task, `bm25` alone solves one prefect task. The abstract's "solves exactly the same 18 of 54" is false as a statement about tasks and must be corrected. The gate's solved set equals `fixed_hybrid`'s.

## 5. Floor effects and equivalence

- Holdout: `yt-dlp` (27 tasks) and `moto` (6) show zero hits for both methods, so they cannot discriminate. 33 of 95 holdout tasks are therefore uninformative for method comparison.
- No equivalence test (e.g. TOST) was pre-specified or run. The text must say "no difference detected", never "equivalent".
- The pilot was not powered for small differences: with 54 tasks and 6 clusters, differences below roughly one to two tasks per repository are indistinguishable from zero.

## 6. Multiplicity and pre-specification (U)
Many conditions and policies were compared. Only the holdout's Q3 and reporting rules were pre-registered (`docs/HOLDOUT_PREREGISTRATION.md`). Pilot analyses are exploratory and must be labelled so. No multiplicity adjustment was applied; none is claimed.
