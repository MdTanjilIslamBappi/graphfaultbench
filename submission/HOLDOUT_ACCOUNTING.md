# Repository-level holdout: accounting and provenance

Audit date 2026-10-22. Pre-registration `docs/HOLDOUT_PREREGISTRATION.md` committed in `f337085` (11:14 +0600); result files written 11:23-16:49. Run code revision `f337085`; results committed in `27506a9`. Recomputation: stdlib script output `results/analysis/holdout_audit.json`, plus `scripts/paired_analysis.py`.

## Expected versus observed rows

Per task: 5 methods x (1 healthy-control row + 4 operators x 2 corrupted severities) = 5 x 9 = 45 rows. Severity 0.0 is evaluated once as `healthy_control`, not once per operator.

| repository | tasks | expected rows (45/task) | observed |
|---|---|---|---|
| django/django | 35 | 1,575 | 1,575 |
| yt-dlp/yt-dlp | 27 | 1,215 | 1,215 |
| tobymao/sqlglot | 15 | 675 | 675 |
| sympy/sympy | 7 | 315 | 315 |
| getmoto/moto | 6 | 270 | 270 |
| matplotlib/matplotlib | 5 | 225 | 225 |
| **total** | **95** | **4,275** | **4,275** |

Gate rows: 95 x 9 = 855 observed 855. All 95 tasks have exactly 45 rows. Exclusions: 0 (`n_excluded_tasks` = 0 and no excluded ids in every `gold_resolution_reports.json`).

## Denominators

- Healthy-graph hit@5: 95 tasks. bm25 21/95 = 0.221; fixed_hybrid 23/95 = 0.242; gate 23/95; graph_expansion 20/95 = 0.211; repomap 19/95 = 0.200.
- Per-repository healthy hits (bm25 / fixed_hybrid): Django 12/14 of 35; sqlglot 4/4 of 15; sympy 2/2 of 7; matplotlib 3/3 of 5; moto 0/0 of 6; yt-dlp 0/0 of 27. The +2 difference is entirely Django.
- Each corrupted cell (method, operator, severity) has denominator 95. fixed_hybrid ranges 21-23 hits (0.221-0.242); bm25 is 21 in every cell; graph_expansion falls to 18/95 (0.189) under `stale_rewire` at both severities, the lowest cell; repomap 19-20.
- Gate: policy `hybrid` on 855/855 rows and hit@5 equal to fixed_hybrid on 855/855 rows.
- Zero-hit repositories: yt-dlp and moto (33 of 95 tasks) never score for bm25 or fixed_hybrid in any cell, a floor effect that makes them uninformative about degradation.

## Provenance and separation

- Holdout repositories: django, yt-dlp, sqlglot, sympy, moto, matplotlib. Earlier results contain only mypy, dask, prefect, numpy, scipy, aiohttp (64 unique task ids). Repository overlap: none. Task-id overlap: none (checked over every earlier `results/**/*.csv|jsonl`; the dev and evaluation tasks of the pilot are included in those).
- Gate thresholds (0.6, 0.5, 0.1) are constructor defaults present since the Phase 1 commit `1090b43` (2026-10-16), before any holdout work; no tuning on the holdout.
- Not checked: whether the holdout repositories were examined informally before pre-registration (no record either way).

## Statistics

Paired fixed_hybrid minus bm25 healthy difference +0.021 (2/95), repository-clustered bootstrap CI [0.000, 0.046]. The lower bound is exactly zero because many resamples contain only tied repositories; the interval does not establish an effect. Provisional preview without Django gave 0.000. One seed, edge-only operators, six clusters: descriptive only.

## Discrepancies found

None in the counts. One earlier-draft wording issue is corrected in the manuscript: the editorial error "an evaluation set,." in the split description.

## Exact bootstrap and condition arithmetic (added 2026-10-22)

Conditions per task: 4 operators x {0.5, 0.75} + 1 shared healthy control = 9 (not 4 x 3 = 12, because severity 0 is the same graph for every operator). 95 x 9 = 855 rows per policy; 5 policies (no WeightedDiagnosticGate in the holdout) = 4,275. Pilot gate rows: 54 tasks x 30 = 1,620, i.e. 1,458 corrupted + 162 healthy.

`scripts/audit_holdout_ci.py` enumerates all 6^6 = 46,656 repository resamples (no Monte-Carlo error) for the healthy fixed_hybrid - bm25 difference: estimate 0.0211, percentile CI [0.000, 0.0455], matching the stored [0.000, 0.0455]. 33.5% of draws give exactly zero and none is negative, because the only non-zero repository is Django (two tasks, both favouring fixed_hybrid). The interval's lower bound of 0.000 is a property of this degenerate resampling distribution, not strong evidence of an effect. Output: `results/analysis/holdout_exact_bootstrap.json`.
