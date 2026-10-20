# Node-omission corruption operator — dev-split evidence (Phase 3)

Status: experiment run complete. All numbers below are read directly from
`results/node_omission_dev/metrics.csv`, `run_manifest.json`,
`graph_reports.json` and `gold_resolution_reports.json`, produced by
`experiments/pilot_a/run_node_omission_experiment.py`. No number in this
document has been invented, extrapolated, or carried over from a prior
projection.

**Regenerated 2026-10-18/19 with the fixed graph builder** (the
duplicate-node-id bug fixed 2026-10-17 — see `research/decision_log.md`),
replacing the original 2026-10-17 run in place. Pre-fix numbers are
preserved in git history and summarised, with what changed, in
`research/decision_log.md`'s 2026-10-18 regeneration entry. Configuration,
repositories, commits (from cache) and seeds are identical to the pre-fix
run; only the graph-construction code differs.

This document is the scoped follow-up authorised in `research/go_no_go.md`
§4 item 2 and described as not-yet-attempted in
`research/novelty_assessment.md` §3: run the existing (but previously
unwired) `node_omission` operator on real data, and use the resulting
empirical signal distribution to inform — not blindly apply — a judgement
about `DiagnosticGate`'s `isolated_ceiling` threshold.

**This is dev-split evidence only.** It is not validated against, and does
not modify, Phase 2's frozen eval-set results in `results/pilot/`. Any
decision to actually change `isolated_ceiling` (or any other threshold) and
re-score the 40-task eval set would be a separate, clearly-labelled
follow-up — not something this document claims to have done.

## 1. Run provenance and the dev/eval separation constraint

- Dataset: Loc-Bench V1 test split, `manifests/raw_data/loc_bench_v1_test.parquet`,
  sha256 `8df0833c2c1276c5837aab923d489ab97d7654529abe759d0f59242c4978a662`
  — identical file to Phase 2's (verified by hash match), not re-downloaded
  or altered.
- Repositories/commits/seeds: identical to Phase 2 (`python/mypy`,
  `dask/dask`, `PrefectHQ/prefect`, 41 commits, seeds `[1, 2, 3]`), reusing
  the cached commit-pinned tarball snapshots already fetched by Phase 2
  (`manifests/repo_cache/`, symlinked into this environment rather than
  re-downloaded).
- Severities: `[0.0, 0.25, 0.5, 0.75]`, matching `configs/pilot_a.yaml`.
- **Constraint enforced in code, not just prose:** the script collects the
  Phase-2 eval-task ids and the dev-task ids separately while iterating,
  asserts they are disjoint, and asserts that every scored task id is a
  dev-task id. Console output from the real run:

  ```
  Node-omission dev-split experiment complete: 7 dev tasks scored,
  40 Phase-2 eval tasks NOT touched (enforced by assertion), 0 excluded
  (gold unresolved, from Phase 2's resolution logic re-run here).
  Wrote 84 rows to results/node_omission_dev.
  Wall time: 306.9s, peak RSS: 794 MiB
  ```

  7 dev tasks and 40 eval tasks matches Phase 2's reported split exactly
  (`reports/pilot_results.md` §2), confirming `is_dev_split` partitions the
  same 47 resolved rows identically here.
- Of the 7 dev tasks, 5 are from `PrefectHQ/prefect` and 2 from
  `dask/dask`; none are from `python/mypy`. This is a consequence of the
  deterministic sha256-based split applied to a small (47-row) population,
  not a deliberate selection — see §6 (limitations) for what this means for
  how far this evidence generalises.
- 84 raw rows = 7 dev tasks × 3 seeds × 4 severities, exactly as expected.

## 2. What was measured

For every dev task × seed × severity, `node_omission(graph, severity, seed)`
was applied to the task's commit graph (severity 0.0 is the unmodified
graph, reusing the same `healthy_control` convention as Phase 2), and
`compute_diagnostics` — the exact function `DiagnosticGate` calls at
runtime — was called directly on the resulting graph to obtain
`node_coverage`, `anchor_confidence` and `isolated_node_rate`. No formula
was reimplemented separately. A fresh `BM25Index` was built from each
corrupted graph's surviving nodes (rather than reusing a cached full-graph
index, as Phase 2 safely did for its edge-only operators), because
`node_omission` changes the node set itself, and a stale index could let a
hidden node's text still contribute to `anchor_confidence`.

Gold-hidden detection (`src/gemma_research/evidence/gold_visibility.py`,
new in this phase, unit-tested in `tests/test_gold_visibility.py`) checks
whether a task's gold node id(s) fall inside the operator's
`hidden_node_ids` set, since `node_omission`'s own docstring is explicit
that gold labels are left untouched and callers must detect this
separately rather than silently scoring a hidden-gold task as an ordinary
miss.

## 3. Diagnostic signal distributions, by severity (n = 21 rows per severity)

| Severity | `node_coverage` mean (min–max) | `isolated_node_rate` mean (min–max) | `anchor_confidence` mean (min–max) |
|---|---|---|---|
| 0.00 | 1.000 (1.000–1.000) | 0.003 (0.001–0.005) | 1.000 (1.000–1.000) |
| 0.25 | 0.750 (0.750–0.750) | 0.064 (0.028–0.123) | 1.000 (1.000–1.000) |
| 0.50 | 0.500 (0.500–0.500) | 0.166 (0.098–0.243) | 1.000 (1.000–1.000) |
| 0.75 | 0.250 (0.250–0.250) | 0.385 (0.236–0.473) | 1.000 (1.000–1.000) |

`node_coverage` is now exact to three decimal places at every severity
(1 − severity precisely), tighter than the pre-fix run's 0.748/0.498/0.248
— with duplicate node objects collapsed, `node_omission`'s hidden-fraction
selection now operates on the true distinct-node population rather than
one inflated by duplicates, removing the small pre-fix jitter.

`isolated_node_rate` histogram (bin width 0.1, count of 21 rows per
severity falling in each bin):

| Severity | [0.0,0.1) | [0.1,0.2) | [0.2,0.3) | [0.3,0.4) | [0.4,0.5) |
|---|---|---|---|---|---|
| 0.00 | 21 | 0 | 0 | 0 | 0 |
| 0.25 | 17 | 4 | 0 | 0 | 0 |
| 0.50 | 1 | 14 | 6 | 0 | 0 |
| 0.75 | 0 | 0 | 2 | 11 | 8 |

**`isolated_node_rate` still never crosses the gate's `isolated_ceiling =
0.5` threshold anywhere in this dataset.** The single highest value
observed across all 84 rows is 0.4726 (up slightly from the pre-fix run's
0.4664, still below the ceiling). This is higher than Phase 2's edge-only
maximum (now 0.4231 under `missing_edges` at severity 0.75, up from the
pre-fix run's 0.311), consistent with node removal being a more disruptive
corruption for connectivity than edge removal alone, but it is still a
negative/null result against the specific question asked: under
`node_omission`, at the severities tested, on this dev split,
`isolated_node_rate` does not exceed 0.5.

`anchor_confidence` remains saturated at exactly 1.0 in all 84 rows, at
every severity including 0.75 (where a median of 75% of nodes are hidden).
This reinforces, under a different corruption type, the concern already
raised in `research/novelty_assessment.md` §3 point 3: the `/ 10.0`
normalisation constant in `anchor_confidence = min(1.0, top_bm25_score /
10.0)` appears to saturate well before any corruption severity tested in
either pilot removes enough signal to matter, which calls into question
whether this signal can ever contribute to `choose_policy`'s branching in
practice on corpora of this scale.

## 4. `node_coverage`, not `isolated_node_rate`, is what actually changes the gate's behaviour here

This is the most consequential finding of this experiment, and it reframes
the question asked in `research/novelty_assessment.md` §3. Applying the
real, **unmodified** `DiagnosticGate.choose_policy` (default thresholds:
`coverage_floor = 0.6`, `isolated_ceiling = 0.5`, `anchor_floor = 0.1`) to
each row's measured diagnostics:

| Severity | `hybrid` | `lexical_only` |
|---|---|---|
| 0.00 | 21 | 0 |
| 0.25 | 21 | 0 |
| 0.50 | 0 | 21 |
| 0.75 | 0 | 21 |

Unlike Phase 2 (100% `hybrid` on 1,200/1,200 rows), the gate **does**
differentiate under `node_omission`: 42/84 rows (50%) select `hybrid` and
42/84 (50%) select `lexical_only` — unchanged by the graph-builder fix,
down to the exact row count. The switch happens because `node_coverage`
drops below `coverage_floor = 0.6` at severity ≥ 0.5 (mean 0.500 at
severity 0.5, 0.250 at severity 0.75) — exactly the condition
`node_coverage` was designed to detect, per `research/novelty_assessment.md`
§2's observation that this signal is structurally insensitive to edge-only
corruption but should respond to node-level corruption. `isolated_node_rate`
plays no role in this particular switch, because `node_coverage` already
fails the `graph_reliable` conjunction before `isolated_node_rate`
approaches its own ceiling.

This means the differentiation observed here is evidence that
`DiagnosticGate`'s adaptivity is *not* inherently non-functional — it
responds correctly to the one class of corruption its `node_coverage`
signal was built for. It is not evidence that the `isolated_ceiling`
threshold specifically is well-calibrated, nor that the gate would
differentiate under corruption types that degrade connectivity without
removing nodes (which is exactly Phase 2's edge-only scenario, where this
mechanism cannot fire).

## 5. How often the gold answer itself was hidden

Because `node_omission` leaves `gold_node_ids` untouched by design, a
nontrivial fraction of dev tasks under this operator have their correct
answer removed from the candidate pool entirely — a different failure mode
from an ordinary ranking miss, since no retrieval method, however good,
can recover an answer that is not a candidate.

| Severity | Tasks with ≥1 gold id hidden | Mean fraction of a task's gold ids hidden |
|---|---|---|
| 0.00 | 0/21 (0%) | 0.000 |
| 0.25 | 7/21 (33%) | 0.190 |
| 0.50 | 11/21 (52%) | 0.389 |
| 0.75 | 20/21 (95%) | 0.810 |

The severity-0.5 row changed the most under the graph-builder fix (was
17/21, 81%; now 11/21, 52%) — exactly the kind of shift expected once
`node_omission`'s hidden-node selection operates on the true, deduplicated
node population rather than one that previously double-counted some
nodes. The severity-0.25 and -0.75 mean fractions happen to be identical
to the pre-fix run despite different task counts; with only 21 rows this
is plausible coincidence, not a claim that these two rows are somehow
unaffected by the fix. At severity 0.5 and above, a large majority of dev
tasks still have at least part of their gold answer hidden. This is
itself a property worth stating plainly: any future retrieval-accuracy
evaluation run under `node_omission`
at these severities would need to report hit-rate metrics separately for
gold-hidden vs. gold-visible tasks (or exclude gold-hidden tasks and report
the exclusion count, mirroring the gold-resolution-exclusion convention
already used in `build_tasks_for_commit`), because a "miss" on a
gold-hidden task measures something structurally different from a miss
caused by weak ranking. This experiment only measured diagnostic signals,
not retrieval accuracy, so no such metric was computed here — this is
flagged as a requirement for any follow-up that does measure accuracy
under `node_omission`.

## 6. What this does and does not support for `isolated_ceiling`

The evidence gathered here does **not** support lowering `isolated_ceiling`
as a way to make the gate respond to node-level corruption, because
`node_coverage` already does that job (§4) — lowering `isolated_ceiling`
would have no observable effect on `choose_policy`'s output in this
dataset, since every row where `isolated_node_rate` is elevated (severity
≥ 0.5) already has `node_coverage` below its own floor.

Combining this dataset's `isolated_node_rate` distribution with Phase 2's
(edge-only, max 0.4231, `node_coverage` always 1.0), a ceiling informed by
both would need to sit somewhere below the current empirical ceiling of
roughly 0.42–0.47 to ever bind under either corruption family studied so
far, e.g. a value in the region of 0.35–0.40 would begin to trigger on the
highest-severity rows of both experiments without flipping any
`healthy_control` row (all `healthy_control` rows measured in both pilots
are below 0.005). This range is higher than the pre-fix run's suggested
0.30–0.35, because both experiments' maxima rose slightly under the
graph-builder fix (§3); it is reported here as what the regenerated
distribution looks like,
**not as a recommendation to adopt a specific new value**: the sample
behind it is small (21 rows per severity, only 2 of 3 repositories
represented in the dev split — see §7), and no value has been evaluated
against the frozen eval set. Actually changing `isolated_ceiling` and
re-scoring the 40 eval tasks under the full corruption-operator suite would
be the necessary next step to turn this observation into a validated
decision, and is explicitly not undertaken here.

## 7. Limitations specific to this experiment

- **Dev-split evidence only, small n.** 7 dev tasks, 21 rows per severity,
  drawn from only 2 of the 3 pilot repositories (5 `PrefectHQ/prefect`, 2
  `dask/dask`, 0 `python/mypy`) — a consequence of applying a
  deterministic 20% hash-based split to a 47-row population, not a
  deliberate sampling choice. Conclusions here should not be assumed to
  hold for `python/mypy`, which is entirely absent from this evidence.
- **No repository-clustered bootstrap was computed.** Unlike
  `reports/pilot_results.md`, this document reports raw means/min/max per
  severity rather than a clustered-bootstrap confidence interval, because
  the question asked (does a diagnostic signal ever cross a fixed
  threshold) is a direct empirical question about the observed
  distribution, not a comparison between methods' point estimates.
- **Duplicate node ids, originally discovered in this phase, fixed as of
  2026-10-17 and applied in this regenerated run.** The original
  (2026-10-17) version of this experiment discovered that
  `build_graph_from_source` could emit more than one `Node` object sharing
  the same `node_id` (24–45 duplicate ids per commit across the 7
  dev-task commits, roughly 0.2–0.4% of each graph's node count), caused
  by `@typing.overload` stubs and occasional genuine same-name
  redefinitions. That bug is now fixed (`research/decision_log.md`,
  2026-10-17 entry) and this document's numbers were regenerated with the
  fix applied — `node_coverage`'s now-exact 1 − severity values (§3) are a
  direct, visible consequence of the fix removing the small amount of
  jitter duplicate ids previously introduced. This is no longer an open
  limitation for the numbers reported in this document; it remains
  relevant historical context for why the pre-fix numbers (preserved in
  git history) differed slightly.
- **Only diagnostic signals were measured, not retrieval accuracy.** This
  experiment does not report `hit_at_k`, `mrr`, or any other accuracy
  metric under `node_omission`; §5 explains why a future accuracy run under
  this operator needs a gold-hidden-aware scoring convention before such
  numbers would be meaningful.
- **Single run, not repeated independently.** As with Phase 2, the pipeline
  is otherwise deterministic (static analysis, no stochastic model
  inference); seed variation (`[1, 2, 3]`) is the only randomness source
  and is already reflected in the ranges reported above.
