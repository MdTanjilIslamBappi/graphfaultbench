# Repository-level holdout — pre-registration (2026-10-22, written before any run)

**Purpose.** The original pilot shares repositories between its development and evaluation tasks, so it says nothing about unseen repositories. This holdout uses six Loc-Bench V1 repositories that appear in no earlier experiment: `tobymao/sqlglot`, `yt-dlp/yt-dlp`, `django/django`, `getmoto/moto`, `sympy/sympy`, `matplotlib/matplotlib` (≈95 tasks).

**Fixed before running.** Code and thresholds identical to the pilot (`DiagnosticGate` defaults); no tuning. Seed 1; severities 0, 0.5, 0.75; operators `missing_edges`, `high_centrality_edges`, `stale_symbol_refs`, `stale_rewire`; all five original methods; every resolved task scored (`dev_fraction: 0`). Single seed because the pilot showed seeds change nothing material and cost must be bounded.

**Questions (descriptive, not significance tests).**
1. Q1: On healthy graphs, is `fixed_hybrid − bm25` (hit@5) different from 0? Paired difference with repository-clustered bootstrap (6 clusters, 5,000 resamples, `scripts/paired_analysis.py`).
2. Q2: Does any method's hit@5 fall with severity under any operator?
3. Q3: Does `DiagnosticGate` equal `fixed_hybrid` on every row, as in the pilot?

**Reporting rules.** All results reported whatever the direction; exclusions (gold-resolution failures) counted and listed; no post-hoc policy. Anything beyond Q1–Q3 is labelled exploratory. Licence caveat unchanged: Loc-Bench V1 licence unstated; raw data not redistributed.
