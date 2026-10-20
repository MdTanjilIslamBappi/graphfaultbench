# Coverage-floor eval-split accuracy validation (Phase 4)

**`coverage_floor`, `isolated_ceiling` and `anchor_floor` were not changed,
tuned, swept, or fit on this data.** This document validates the
already-fixed, development-time-set values from Phase 2
(`coverage_floor = 0.6`, `isolated_ceiling = 0.5`, `anchor_floor = 0.1`)
against previously-unused eval data. The experiment script
(`experiments/pilot_a/run_coverage_floor_eval.py`) asserts these three
values against `DiagnosticGate.__init__`'s own default parameters before
running anything; the real run's `run_manifest.json` confirms
`gate_thresholds = {"coverage_floor": 0.6, "isolated_ceiling": 0.5,
"anchor_floor": 0.1}`. No threshold was changed anywhere in this phase.

Status: experiment run complete. All numbers below are read directly from
`results/coverage_floor_eval/metrics.csv`, `summary.json`,
`gold_hidden_by_severity.json`, `run_manifest.json` and
`graph_reports.json`, produced by
`experiments/pilot_a/run_coverage_floor_eval.py`. No number in this
document has been invented, extrapolated, or carried over from a prior
projection.

**Regenerated 2026-10-18/19 with the fixed graph builder** (the
duplicate-node-id bug fixed 2026-10-17 — see `research/decision_log.md`),
replacing the original 2026-10-17 run in place. Configuration,
repositories, commits (from cache) and seeds are identical to the pre-fix
run; only the graph-construction code differs. **This regeneration changed
more than cosmetic numbers: at severity 0.75, the point-estimate direction
between `fixed_hybrid` and `bm25`/`diagnostic_gate` reverses from the
pre-fix run (§5).** The pre-fix numbers and a full account of what changed
are preserved in git history and in `research/decision_log.md`'s
2026-10-18/19 regeneration entry.

## 0. The question this document answers

Phase 3 (`research/node_removal_operator.md`) showed that `DiagnosticGate`
*can* respond to `node_omission` corruption — `node_coverage` drops below
`coverage_floor` at severity >= 0.5, causing the gate to switch from
`hybrid` to `lexical_only` on half of its 84 dev-split rows. Phase 3 only
measured *which policy got chosen*; it explicitly did not measure whether
the switch helps retrieval accuracy, and it was scored only on the 7
dev-split tasks, never the 40 held-out eval tasks. This document closes
both gaps: it scores `bm25_rank`, `fixed_hybrid_rank`, and
`DiagnosticGate().rank(...)` against `node_omission`-corrupted graphs on
the 40 eval tasks, and reports whether the gate's policy switch actually
produces better accuracy than the two simpler baselines would have
achieved on the same corrupted graphs.

**Headline finding, stated plainly up front, updated for the regenerated
run:** on this eval set, the gate's policy switch shows **no measurable
accuracy benefit** over `fixed_hybrid` — that overall conclusion is
unchanged. What changed under the graph-builder fix is *which direction*
the point estimates point in at the two severities where the switch
happens. At severity 0.5, `fixed_hybrid` still scores higher than
`bm25`/`diagnostic_gate` on `hit_at_5` and `strict_acc_at_5`, as in the
pre-fix run. **At severity 0.75, this reverses: `bm25`/`diagnostic_gate`
now score higher than `fixed_hybrid`** on those same two metrics — the
opposite of the pre-fix run, where `fixed_hybrid` was higher at both
severities. The gate's switch therefore moves, by point estimate, away
from the better-performing baseline at severity 0.5 and toward it at
severity 0.75 — a mixed, not a consistent, direction. Every interval
involved is wide and heavily overlapping (only 3 repository clusters), so
none of this was ever a statistically significant difference, and it
still is not; what has changed is that the *point-estimate* story is now
"mixed across the two switching severities" rather than "consistently
unfavourable to the gate." §5 gives the full table and traces the reversal
to a genuinely different gold-visible task sample at severity 0.75, not
to an error in either run.

## 1. Run provenance and the eval/dev separation constraint

- Dataset: Loc-Bench V1 test split, `manifests/raw_data/loc_bench_v1_test.parquet`,
  sha256 `8df0833c2c1276c5837aab923d489ab97d7654529abe759d0f59242c4978a662`
  — identical file to Phase 2 and Phase 3's (verified by hash match in this
  run), not re-downloaded or altered.
- Repositories/commits/seeds: identical to Phase 2/3 (`python/mypy`,
  `dask/dask`, `PrefectHQ/prefect`, 41 commits, seeds `[1, 2, 3]`), reusing
  Phase 2's cached commit-pinned tarball snapshots (`manifests/repo_cache/`,
  symlinked into this worktree from the main checkout rather than
  re-downloaded — no network cost was incurred for repository content;
  only the small Loc-Bench parquet file, already cached, was read).
- Severities: `[0.0, 0.25, 0.5, 0.75]`, matching `configs/pilot_a.yaml` and
  Phase 3's convention (0.0 = healthy control).
- **Constraint enforced in code, not just prose:** the script collects the
  eval-task and dev-task ids separately while iterating, asserts they are
  disjoint, and asserts that every scored task id is an eval-task id (the
  mirror image of Phase 3's dev-only assertion). Real console output from
  the run:

  ```
  Coverage-floor eval-split experiment complete: 40 eval tasks scored,
  7 dev tasks NOT touched (enforced by assertion), 0 excluded (gold
  unresolved, from Phase 2's resolution logic re-run here). Wrote 1440
  rows to results/coverage_floor_eval.
  Wall time: 1285.8s, peak RSS: 827 MiB
  ```

  40 eval tasks and 7 dev tasks matches Phase 2's reported split exactly
  (`reports/pilot_results.md`: "Per-repository evaluation-task counts:
  `python/mypy` 11, `dask/dask` 18, `PrefectHQ/prefect` 11"), and this
  run's own per-repo eval-task counts, derived from `metrics.csv`
  (33/54/33 task×seed rows at severity 0.0, divided by 3 seeds), are
  11/18/11 — an exact match, confirming `is_dev_split`/`build_tasks_for_commit`
  partition the same 47 resolved rows identically here as in Phase 2 and
  Phase 3.
- 1,440 raw rows = 40 eval tasks x 3 seeds x 4 severities x 3 methods
  (`bm25`, `fixed_hybrid`, `diagnostic_gate`), exactly as expected. 0 tasks
  excluded for gold-resolution failure (re-running Phase 2's exact
  resolution logic over the same dataset gives the same result).
- Wall time for this run was 1,285.8 s (about 21.4 minutes), with peak RSS
  827 MiB. This is faster than Phase 2's 4,683.2 s for the same 40 tasks
  under three edge-only operators and five methods — expected, since this
  run omits the `repomap` baseline (the only method using iterative
  PageRank, the slowest component of Phase 2) and scores only one
  corruption operator (`node_omission`) instead of three. It should not be
  read as evidence that `node_omission` itself is cheaper to apply than
  the edge-only operators; the two runs are not controlled for that
  variable. No repository content was re-downloaded (cache hit), so this
  1,285.8 s reflects compute only, not network time; a fresh environment
  without the cached tarballs would add whatever time `fetch_repo_snapshot`
  needs to download ~41 GitHub tarballs, which Phase 3 did not have to
  measure either (it also reused the cache) and which this run likewise
  did not measure.

## 2. What was measured

For every eval task x seed x severity, `node_omission(graph, severity,
seed)` was applied to the task's commit graph (severity 0.0 is the
unmodified graph, the `healthy_control` convention), and a fresh
`BM25Index` was built from the corrupted graph's surviving nodes (per
corrupted-graph instance, i.e. once per (commit, seed, severity) and
reused across every eval task sharing that commit — a performance
optimisation over Phase 3's per-task rebuild that does not change any
score, since the index depends only on the current node set and query
text, never on which task is being scored). Three methods were then run
against the identical corrupted graph and shared index:

- `bm25_rank` (lexical-only baseline),
- `fixed_hybrid_rank` (static lexical/graph-expansion blend),
- `DiagnosticGate().rank(...)` (policy chosen from `compute_diagnostics`'
  real, unmodified signals).

All three functions were imported and called exactly as defined in
`src/gemma_research/evidence/retrieve.py` — none were reimplemented.
Metrics (`hit_at_1`, `hit_at_3`, `hit_at_5`, `strict_acc_at_5`, `mrr`) were
computed with the existing functions in
`src/gemma_research/metrics/scoring.py`, likewise unmodified.
`any_gold_hidden` / `gold_hidden_fraction` were computed with the existing
`src/gemma_research/evidence/gold_visibility.py` helpers, exactly as Phase
3 used them.

## 3. Diagnostic signal distributions on the eval set (n = 120 rows per severity)

| Severity | `node_coverage` mean (min–max) | `isolated_node_rate` mean (min–max) | `anchor_confidence` mean (min–max) |
|---|---|---|---|
| 0.00 | 1.0000 (1.0000–1.0000) | 0.0032 (0.0015–0.0052) | 1.0000 (1.0000–1.0000) |
| 0.25 | 0.7500 (0.7499–0.7501) | 0.0524 (0.0258–0.1239) | 1.0000 (1.0000–1.0000) |
| 0.50 | 0.5000 (0.4999–0.5001) | 0.1487 (0.0900–0.2391) | 1.0000 (1.0000–1.0000) |
| 0.75 | 0.2500 (0.2499–0.2501) | 0.3609 (0.2289–0.4705) | 1.0000 (1.0000–1.0000) |

`node_coverage` is now exact to three decimal places (1 − severity) at
every row, tighter than the pre-fix run's 0.7472/0.4970/0.2481 — the same
effect the graph-builder fix produced in Phase 3 (§3 of
`research/node_removal_operator.md`): with duplicate node objects
collapsed, `node_omission`'s hidden-fraction selection operates on the
true distinct-node population. These numbers remain close to Phase 3's
regenerated dev-split numbers (`node_coverage` exactly 0.750/0.500/0.250
at the same severities, `isolated_node_rate` rising with severity,
`anchor_confidence` saturated at 1.0 throughout), which is expected: both
runs apply the same deterministic `node_omission` operator with the same
seeds to graphs built the same way, just over disjoint task sets drawn
from the same 3 repositories. `isolated_node_rate` again never crosses
`isolated_ceiling = 0.5` anywhere in this dataset; the single highest
value observed across all 480 `diagnostic_gate` rows is 0.4705 (down
slightly from the pre-fix run's 0.4867), marginally higher than Phase 3's
regenerated dev-split maximum of 0.4726 but still below the ceiling.
`anchor_confidence` remains saturated at exactly 1.0 in every row at every
severity, reinforcing the same concern raised in
`research/novelty_assessment.md` and `research/node_removal_operator.md`
about this signal's normalisation saturating before it can contribute to
`choose_policy`'s branching at this corpus scale.

Calling the real, unmodified `DiagnosticGate.choose_policy` on every row's
measured diagnostics:

| Severity | `hybrid` | `lexical_only` |
|---|---|---|
| 0.00 | 120 | 0 |
| 0.25 | 120 | 0 |
| 0.50 | 0 | 120 |
| 0.75 | 0 | 120 |

The gate differentiates perfectly by severity on the eval set too (not a
mix within a severity): 100% `hybrid` at 0.0/0.25, 100% `lexical_only` at
0.5/0.75, driven entirely by `node_coverage` crossing `coverage_floor`
between severity 0.25 and 0.5 — the same mechanism Phase 3 identified on
the dev split. This policy pattern is unchanged, row-count for row-count,
by the graph-builder fix. `isolated_node_rate` plays no role in any switch
observed here, for the same reason Phase 3 gave: `node_coverage` already
fails the `graph_reliable` conjunction before `isolated_node_rate`
approaches its own ceiling.

## 4. Gold-hidden accounting (not silently dropped)

`node_omission` leaves `gold_node_ids` untouched by design, so a
substantial fraction of (task, seed) combinations at higher severities
have their gold answer removed from the candidate pool entirely — a
failure mode no ranking method can recover from, since the answer is not
a candidate at all. These rows are excluded from the accuracy subset
below, and the exclusion is reported explicitly rather than silently
dropped, mirroring `build_tasks_for_commit`'s gold-resolution-exclusion
convention:

| Severity | Task×seed combos | Gold-hidden (excluded) | Fraction excluded | Gold-visible (scored) |
|---|---|---|---|---|
| 0.00 | 120 | 0 | 0.0% | 120 |
| 0.25 | 120 | 46 | 38.3% | 74 |
| 0.50 | 120 | 71 | 59.2% | 49 |
| 0.75 | 120 | 98 | 81.7% | 22 |

Severity 0.0 and 0.75's totals are unchanged by the graph-builder fix
(0 and 98 hidden respectively); severity 0.25 and 0.5 shifted (was 42/120
and 72/120). This is an expected consequence of the fix, not an anomaly:
`node_omission`'s hidden-node selection operates on the deduplicated node
population now, so a different subset of nodes — and therefore a
different subset of gold ids — ends up hidden at a given severity.
Critically, at severity 0.75 **the total count is unchanged (22) but the
membership is not**: comparing the exact (task, seed) pairs gold-visible
at severity 0.75 before and after the fix, 15 of the 22 are different
tasks. The identical total is coincidence, not evidence that this
severity's evaluation subset is stable under the fix.

Per-repository breakdown of the gold-visible subset (from
`gold_hidden_by_severity.json` and `metrics.csv`):

| Severity | `python/mypy` visible | `dask/dask` visible | `PrefectHQ/prefect` visible |
|---|---|---|---|
| 0.00 | 33 | 54 | 33 |
| 0.25 | 22 | 32 | 20 |
| 0.50 | 15 | 20 | 14 |
| 0.75 | 7 | 9 | 6 |

The severity-0.75 per-repository split also changed despite the same
total (was 11/8/3, now 7/9/6) — consistent with the membership churn just
described. `PrefectHQ/prefect`'s severity-0.75 sample size doubled (3 to
6), which matters for §5: the pre-fix run's severity-0.75 result rested on
a thinner, more `python/mypy`-heavy sample than the regenerated one does.
All three repositories still contribute at least one gold-visible row at
every severity (the clustered bootstrap below always has `n_repos = 3`),
but the per-repository sample is thin at the highest severity and this
should be read as a low-power regime, not a null result with strong
statistical backing.

## 5. Accuracy: does the gate's switch actually help? (the central question)

All accuracy numbers below are computed on the gold-visible subset only,
per (method, severity), with a repository-clustered bootstrap confidence
interval (`bootstrap_ci_clustered`, `n_resamples = 2000`, `seed = 0`,
matching `configs/pilot_a.yaml`'s convention). Read directly from
`results/coverage_floor_eval/summary.json`.

| Severity | Method | hit@1 | hit@3 | hit@5 | strict_acc@5 | mrr |
|---|---|---|---|---|---|---|
| 0.00 | bm25 | 0.175 [0.00, 0.28] | 0.225 [0.00, 0.39] | 0.275 [0.00, 0.39] | 0.200 [0.00, 0.33] | 0.223 [0.00, 0.35] |
| 0.00 | fixed_hybrid | 0.175 [0.00, 0.28] | 0.225 [0.00, 0.39] | 0.275 [0.00, 0.44] | 0.200 [0.00, 0.33] | 0.229 [0.01, 0.36] |
| 0.00 | diagnostic_gate | 0.175 [0.00, 0.28] | 0.225 [0.00, 0.39] | 0.275 [0.00, 0.44] | 0.200 [0.00, 0.33] | 0.229 [0.01, 0.36] |
| 0.25 | bm25 | 0.149 [0.00, 0.28] | 0.257 [0.00, 0.44] | 0.270 [0.00, 0.47] | 0.203 [0.00, 0.38] | 0.211 [0.00, 0.38] |
| 0.25 | fixed_hybrid | 0.149 [0.00, 0.28] | 0.257 [0.00, 0.44] | **0.338 [0.00, 0.56]** | **0.257 [0.00, 0.44]** | 0.223 [0.00, 0.39] |
| 0.25 | diagnostic_gate | 0.149 [0.00, 0.28] | 0.257 [0.00, 0.44] | 0.338 [0.00, 0.56] | 0.257 [0.00, 0.44] | 0.223 [0.00, 0.39] |
| 0.50 | bm25 | 0.102 [0.00, 0.20] | 0.265 [0.00, 0.50] | 0.265 [0.00, 0.50] | 0.224 [0.00, 0.45] | 0.194 [0.00, 0.37] |
| 0.50 | fixed_hybrid | 0.102 [0.00, 0.20] | 0.265 [0.00, 0.50] | **0.306 [0.00, 0.55]** | **0.265 [0.00, 0.50]** | 0.202 [0.00, 0.37] |
| 0.50 | diagnostic_gate | 0.102 [0.00, 0.20] | 0.265 [0.00, 0.50] | 0.265 [0.00, 0.50] | 0.224 [0.00, 0.45] | 0.194 [0.00, 0.37] |
| 0.75 | bm25 | 0.182 [0.00, 0.44] | 0.273 [0.00, 0.56] | **0.318 [0.00, 0.56]** | **0.318 [0.00, 0.56]** | 0.249 [0.01, 0.53] |
| 0.75 | fixed_hybrid | 0.182 [0.00, 0.44] | 0.273 [0.00, 0.56] | 0.273 [0.00, 0.56] | 0.273 [0.00, 0.56] | 0.245 [0.01, 0.53] |
| 0.75 | diagnostic_gate | 0.182 [0.00, 0.44] | 0.273 [0.00, 0.56] | **0.318 [0.00, 0.56]** | **0.318 [0.00, 0.56]** | 0.249 [0.01, 0.53] |

(All values are point estimates with the `[ci_low, ci_high]` 95%
clustered-bootstrap interval, cross-checked directly against
`results/coverage_floor_eval/summary.json`'s own output, not only
re-derived from `metrics.csv`. Bold marks, at each severity, whichever of
`fixed_hybrid` versus `bm25`/`diagnostic_gate` has the higher point
estimate on `hit_at_5` and `strict_acc_at_5` — **note that this is no
longer always `fixed_hybrid`**: at severity 0.75, `bm25`/`diagnostic_gate`
now hold the higher point estimate, the reverse of severity 0.5 and of
the pre-fix run's result at both severities.)

Three observations follow directly from this table, all independently
re-derived from `metrics.csv`/`summary.json` (not assumed):

1. **`diagnostic_gate` is numerically identical to one of the two
   baselines at every single row, by construction.** `DiagnosticGate.rank`
   does not blend a third ranking; it calls either `bm25_rank` or
   `fixed_hybrid_rank` outright depending on `choose_policy`'s decision.
   Since the policy choice is 100% `hybrid` at severities 0.0/0.25 and
   100% `lexical_only` at 0.5/0.75 (§3), `diagnostic_gate`'s summary row is
   byte-for-byte identical to `fixed_hybrid`'s at 0.0/0.25 and to `bm25`'s
   at 0.5/0.75 — confirmed by comparing the raw per-row rankings, not only
   the aggregated means. This is expected behaviour of the gate as coded,
   not an artefact of this analysis.

2. **`hit_at_1` and `hit_at_3` are identical between `bm25` and
   `fixed_hybrid` at every severity in this dataset.** The two baselines
   only diverge at `hit_at_5`/`strict_acc_at_5`/`mrr`, where
   `fixed_hybrid`'s graph-expansion contribution promotes additional
   correct candidates into the bottom of the top-5 window that pure BM25
   ranking does not reach. This is a property of this dataset's score
   distributions (lexical anchors already dominate the top-3 ranks), not
   a general claim about BM25 versus hybrid ranking.

3. **At the two severities where the gate actually switches policy (0.5
   and 0.75), the point-estimate direction is mixed, not consistent —
   this is the one finding in this document that changed under the
   graph-builder fix, not merely shifted numerically.** At severity 0.5,
   `fixed_hybrid`'s point estimate remains higher than `bm25`'s (and
   therefore the gate's) on `hit_at_5` (0.306 vs 0.265) and
   `strict_acc_at_5` (0.265 vs 0.224), the same direction as the pre-fix
   run (where the gap was larger: 0.396 vs 0.292). **At severity 0.75 this
   reverses: `bm25`/`diagnostic_gate` now score higher than
   `fixed_hybrid`** on `hit_at_5` (0.318 vs 0.273) and `strict_acc_at_5`
   (0.318 vs 0.273) — the pre-fix run had `fixed_hybrid` higher at this
   severity too (0.364 vs 0.273). §4 traces this reversal to a genuinely
   different gold-visible task sample at severity 0.75 after the fix (15
   of 22 task×seed pairs differ, and `PrefectHQ/prefect`'s contribution
   doubled from 3 to 6 rows), not to any error in either run — this is a
   small-sample result that depends materially on exactly which 22 tasks
   end up in the denominator. The confidence intervals at every severity
   are wide and heavily overlapping (driven by only 3 repository clusters,
   as expected for this resampling design with this few clusters — see
   `bootstrap_ci_clustered`'s own docstring on this), so neither direction,
   before or after the fix, was ever a statistically significant
   difference. What is now clearer, precisely because the fix changed the
   direction at one severity while leaving it unchanged at the other, is
   that the pre-fix run's "consistent direction across both severities"
   was itself most plausibly small-sample noise rather than a real effect
   — a result that happened to point the same way twice is weaker evidence
   than it looks, and this regeneration is a direct demonstration of that.

**Conclusion for the question this phase was designed to answer, updated:**
`DiagnosticGate` does not show a measurable accuracy benefit over
`fixed_hybrid` under `node_omission` on the 40-task eval set — that
conclusion is unchanged by the graph-builder fix. What changed is the
supporting detail: the gate's switch to `lexical_only` tracks `bm25`
exactly by construction, and at severity 0.5 that switch still moves away
from `fixed_hybrid`'s (higher) point estimate; at severity 0.75 it now
moves *toward* the higher point estimate instead. Averaged across the two
switching severities, there is no consistent point-estimate advantage or
disadvantage to the gate's switch — which is, if anything, a more secure
basis for the "no measurable benefit" conclusion than the pre-fix run's
result, since that result's apparent consistency has not survived an
unrelated bug fix. This directly answers the open question Phase 3 left
unaddressed, and the answer remains a null result: the gate's demonstrated
ability to *differentiate* policy under node-level corruption (Phase 3's
finding) does not translate into a reliable accuracy advantage, in either
direction, on this eval set.

## 6. What this does and does not support

This evidence does not support retaining `coverage_floor = 0.6` as an
accuracy-improving mechanism under `node_omission`-style corruption on
these three repositories: it changes the gate's chosen policy, but the
policy it switches to does not reliably outperform the one it leaves, on
the pre-registered primary metric (`hit_at_5`) or on
`strict_acc_at_5`/`mrr`. It also does not support the opposite
conclusion — that `fixed_hybrid` is reliably better than `lexical_only`
under this corruption — because the confidence intervals overlap
substantially at every severity, the gold-visible sample shrinks sharply
at severity 0.75 (22 rows), and (§5 item 3) the point-estimate direction
at that severity is not stable even under a graph-construction fix that
changes nothing about the methods being compared. What the evidence does
support, stated carefully: on this specific corruption operator, this
specific dataset, and the pre-existing fixed thresholds, there is no sign
that letting `node_coverage` drive a `hybrid`/`lexical_only` switch is
worth the added complexity over always running `fixed_hybrid` — and the
regeneration in this document makes that "no sign" conclusion more
secure, not less, since the one piece of evidence that looked like a
consistent pattern in the pre-fix run turned out not to survive an
unrelated bug fix. This is consistent with Phase 2's original finding
that the gate was numerically indistinguishable from `fixed_hybrid` under
edge-only corruption (because it never switched at all) — here, under
node-level corruption, it does switch, but the switch's effect on
accuracy is, at best, inconsistent in direction and not statistically
distinguishable from no effect.

No new threshold value is proposed or evaluated here, consistent with the
constraint that this phase validates, not tunes, the existing defaults.

## 7. Limitations specific to this experiment

- **Wide confidence intervals from only 3 repository clusters.** Every
  interval in §5 spans roughly 0.4–0.9 in width, which is an inherent
  consequence of clustering at the repository level with only 3
  repositories (as `bootstrap_ci_clustered`'s own docstring notes: "with
  few clusters this interval is necessarily wide; that width is itself
  informative, not a bug to average away"). The point-estimate direction
  reported in §5 item 3 is *not* consistent across both switching
  severities in the regenerated run (it was in the pre-fix run, before the
  graph-builder fix changed which tasks are gold-visible at severity
  0.75); this inconsistency, surfaced by an unrelated bug fix, is itself
  evidence that neither run's point estimates should be read as
  corroborating evidence beyond a single draw. No statistically
  significant result is claimed, at either severity, in either run.
- **Shrinking, gold-hidden-filtered sample at high severity, and
  sensitive to exactly which tasks fall in it.** The gold-visible subset
  falls from 120 rows at severity 0.0 to 22 rows at severity 0.75 (§4).
  Unlike the pre-fix run, `PrefectHQ/prefect` now contributes 6 visible
  rows at that severity rather than 3, and the task-level membership of
  the 22-row sample is mostly different from the pre-fix run despite the
  same total count. Conclusions at severity 0.75 rest on a particularly
  thin sample whose exact composition changes with small, unrelated
  changes to graph construction, and should be read with that in mind.
- **`diagnostic_gate`'s rows are not independent evidence from one of the
  two baselines.** Because the gate's ranking is literally identical to
  `bm25` or `fixed_hybrid` on every row (§5 item 1), its summary statistics
  are not a third independent data point; they are a re-labelling of
  whichever baseline the policy happened to select. This is stated
  explicitly so a reader does not mistake three similar-looking rows in
  §5's table for three independent confirmations.
- **Duplicate `node_id` values, originally discovered via Phase 3, fixed
  as of 2026-10-17 and applied in this regenerated run.** The pre-fix
  version of this document reported 67/53/77 duplicate `node_id` values on
  one spot-checked commit per repository (0.50–0.71% of each graph's node
  objects) — the same phenomenon Phase 3 flagged. That bug is now fixed
  (`research/decision_log.md`, 2026-10-17 entry), and this document was
  regenerated with the fix applied: §3's exact `node_coverage` values and
  §4/§5's shifted gold-visible samples and accuracy numbers are direct
  consequences of it. This is the single largest-impact limitation this
  document previously carried, and it is no longer open for the numbers
  reported here. It remains relevant historical context for why the
  pre-fix numbers (preserved in git history) differed, including why the
  severity-0.75 point-estimate direction in §5 is not the same in both
  versions of this document.
- **Single run, not independently repeated.** As with Phases 2 and 3, the
  pipeline is deterministic (static analysis, no stochastic model
  inference); seed variation (`[1, 2, 3]`) is the only randomness source
  and is already reflected in the per-row data underlying the bootstrap
  intervals above.
- **Scope of generalisation.** This result is specific to `node_omission`
  as implemented, these three repositories, these 41 commits, and these
  40 eval tasks. It says nothing about whether `DiagnosticGate` would show
  an accuracy benefit under a different node-level corruption model, a
  larger or differently-composed repository sample, or a different
  primary metric than `hit_at_5`.
- **Performance optimisation versus Phase 3.** This script builds one
  `BM25Index` per (commit, seed, severity) and reuses it across every eval
  task sharing that commit, rather than rebuilding it per task as Phase
  3's dev-split script did. This does not change any reported score (the
  index depends only on the corrupted node set and the query text passed
  to `.score()`, never on which task supplied that query), and is recorded
  here only as a difference in implementation detail between the two
  scripts, not a difference in method.
