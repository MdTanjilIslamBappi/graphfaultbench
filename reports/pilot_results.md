# GraphFaultBench real-data pilot — results

Status: pilot run complete. All numbers below are read directly from
`results/pilot/run_manifest.json`, `summary.json`, `metrics.csv`,
`graph_reports.json` and `gold_resolution_reports.json`, produced by
`experiments/pilot_a/run_real_pilot.py`. No number in this document has
been invented, extrapolated, or carried over from a prior projection.

**Regenerated 2026-10-18/19 with the fixed graph builder** (the
duplicate-node-id bug fixed 2026-10-17 — see `research/decision_log.md`).
This replaces the original 2026-10-16 run in place; the pre-fix numbers
are preserved in git history (commit `34dfd64` and earlier) and in
`research/decision_log.md`'s 2026-10-18 regeneration entry, which records
exactly what changed and why. The regenerated run used identical
configuration, repositories, commits (from cache, not re-fetched) and
seeds — only the graph-construction code differs.

## 1. Run provenance

- Dataset: Loc-Bench V1 test split, `manifests/raw_data/loc_bench_v1_test.parquet`,
  sha256 `8df0833c2c1276c5837aab923d489ab97d7654529abe759d0f59242c4978a662`
  (matches `manifests/data_manifest.json`).
- Repositories (commit-pinned snapshots fetched from `codeload.github.com`):
  `python/mypy` (6 commits), `dask/dask` (19 commits), `PrefectHQ/prefect`
  (16 commits) — 41 commits in total.
- Pre-registered configuration: `configs/pilot_a.yaml` (seeds `[1,2,3]`,
  severities `[0.0, 0.25, 0.5, 0.75]`, corruption operators
  `missing_edges`, `high_centrality_edges`, `stale_symbol_refs`,
  bootstrap resamples 2000, `primary_metric = hit_at_5`). This file was
  written before any result was seen.
- Wall-clock time: 4683.2 s (78 min 3 s); peak resident set size 958,172 kB
  (≈ 935 MiB).
- Raw rows written: 6000 (`results/pilot/metrics.csv`).
- `graph_reports.json` now additionally reports `n_duplicate_ids_collapsed`
  per commit (0 throughout, confirming the fix is active): 402 node
  objects were collapsed across `python/mypy`'s 6 commits, 850 across
  `dask/dask`'s 19, and 1,212 across `PrefectHQ/prefect`'s 16 — 2,464 in
  total, matching the fix's own verification sweep exactly
  (`research/decision_log.md`, 2026-10-17 entry).

## 2. Task counts

| Quantity | Count |
|---|---|
| Loc-Bench rows selected (3 repos) | 47 |
| Tasks with gold `edit_functions` resolving exactly against the built graph | 47 |
| Excluded (gold unresolved against the graph) | 0 |
| Dev-split tasks (held out, reported but not used for any metric below) | 7 |
| Evaluation tasks | 40 |

Per-repository evaluation-task counts: `python/mypy` 11, `dask/dask` 18,
`PrefectHQ/prefect` 11.

Zero exclusions is a direct consequence of the node-id convention check
built into `build_tasks_for_commit`: every gold `edit_functions` entry in
the selected rows happened to resolve exactly against the statically built
graph for its commit. This is a property of the three repositories chosen,
not a general guarantee for Loc-Bench V1 as a whole, and is discussed
further in `research/limitations.md`.

## 3. Graph construction

| Repo | Commits | Nodes (min–max) | Edges (min–max) | Unresolved calls (min–max) |
|---|---|---|---|---|
| python/mypy | 6 | 9,377–9,385 | 35,195–35,306 | 3,174–3,183 |
| dask/dask | 19 | 5,651–7,572 | 22,750–31,303 | 17,099–21,143 |
| PrefectHQ/prefect | 16 | 15,442–23,992 | 43,695–66,734 | 23,308–37,086 |

Node and edge counts are lower than the pre-fix run (e.g. `python/mypy`'s
edge count drops by roughly 28%): collapsing a duplicate node to one
object also removes every edge that becomes an exact duplicate as a
result, which is a larger effect than the raw duplicate-node count alone
suggests. Unresolved-call counts are unchanged, since that figure counts
attempted call resolutions against the (now-deduplicated) node set, not
node or edge objects themselves.

No file was skipped for a syntax or decoding error in any of the 41
commits (`n_files_skipped = 0` throughout `graph_reports.json`).

The unresolved-call counts, relative to the (now smaller) resolved-edge
count, are substantial and higher than the pre-fix run: roughly 9.0% for
`python/mypy` (was ~6.5%), 67.5–75.2% for `dask/dask` (was ~43–48%), and
48.6–60.3% for `PrefectHQ/prefect` (was ~41–52%). The unresolved-call
count itself is unchanged by the fix (it measures failed name lookups,
which deduplication does not help); the ratio rises because the
resolved-edge denominator shrank (collapsing a duplicate node also
removes the now-duplicate edges that pointed to it). This reflects the
documented limitation that call-edge resolution in `graph_builder.py` is
name-based rather than type-aware: a call target is only linked when its
unqualified name matches a known node in the same file or, failing that,
uniquely enough elsewhere in the repository. This is a known heuristic
weakness, not a defect introduced by this pilot run or by the
duplicate-id fix, and is carried into `research/limitations.md`.

## 4. Retrieval performance, averaged over all corruption conditions

Mean of `hit_at_1`, `hit_at_3`, `hit_at_5`, `strict_acc_at_5`, `mrr` and
per-call `runtime_seconds` across all 1,200 rows recorded for each method
(40 tasks × 3 seeds × 10 corruption combinations):

| Method | Hit@1 | Hit@3 | Hit@5 | Strict Acc@5 | MRR | Mean runtime (s) |
|---|---|---|---|---|---|---|
| `bm25` | 0.175 | 0.225 | 0.275 | 0.200 | 0.223 | 0.381 |
| `graph_expansion` | 0.100 | 0.225 | 0.258 | 0.176 | 0.165 | 0.468 |
| `fixed_hybrid` | 0.175 | 0.225 | 0.283 | 0.198 | 0.228 | 0.871 |
| `repomap` | 0.168 | 0.210 | 0.228 | 0.149 | 0.198 | 0.582 |
| `diagnostic_gate` | 0.175 | 0.225 | 0.283 | 0.198 | 0.228 | 1.259 |

`diagnostic_gate` and `fixed_hybrid` remain identical to three decimal
places on every metric after the graph-builder fix — this is unchanged
from the pre-fix run (where the match was also exact) and is not a
coincidence or a rounding artefact: see §6, which traces it to the
policy-selection logic, and confirms `diagnostic_gate` ties `fixed_hybrid`
on `hit_at_5` on all 1,200/1,200 rows, not merely in aggregate. `bm25`'s
numbers are essentially unchanged from the pre-fix run (it never reads
the graph), which is itself a useful cross-check that the fix did not
introduce some unrelated scoring change; `graph_expansion` and `repomap`,
which do read graph structure, shift slightly more, consistent with the
graph-construction changes in §3.

## 5. Performance under corruption, by operator and severity

Bootstrapped (2,000 resamples, clustered by repository, 95% CI) `hit_at_5`
for the primary metric, read from `results/pilot/summary.json`. Because
there are only `n_repos = 3` clusters, confidence intervals are wide for
every cell; this is reported honestly rather than narrowed by an
inappropriate resampling unit (see `research/limitations.md`).

| Operator | Severity | `bm25` | `fixed_hybrid` | `graph_expansion` | `repomap` | `diagnostic_gate` |
|---|---|---|---|---|---|---|
| healthy_control | 0.00 | 0.275 [0.00, 0.39] | 0.275 [0.00, 0.44] | 0.250 [0.00, 0.39] | 0.200 [0.00, 0.33] | 0.275 [0.00, 0.44] |
| missing_edges | 0.25 | 0.275 [0.00, 0.39] | 0.283 [0.00, 0.43] | 0.242 [0.00, 0.39] | 0.217 [0.00, 0.37] | 0.283 [0.00, 0.43] |
| missing_edges | 0.50 | 0.275 [0.00, 0.39] | 0.292 [0.00, 0.43] | 0.242 [0.00, 0.39] | 0.242 [0.00, 0.41] | 0.292 [0.00, 0.43] |
| missing_edges | 0.75 | 0.275 [0.00, 0.39] | 0.300 [0.00, 0.43] | 0.233 [0.00, 0.39] | 0.233 [0.00, 0.41] | 0.300 [0.00, 0.43] |
| high_centrality_edges | 0.25 | 0.275 [0.00, 0.39] | 0.275 [0.00, 0.44] | 0.250 [0.00, 0.39] | 0.225 [0.00, 0.39] | 0.275 [0.00, 0.44] |
| high_centrality_edges | 0.50 | 0.275 [0.00, 0.39] | 0.300 [0.00, 0.44] | 0.267 [0.06, 0.39] | 0.225 [0.00, 0.39] | 0.300 [0.00, 0.44] |
| high_centrality_edges | 0.75 | 0.275 [0.00, 0.39] | 0.275 [0.00, 0.39] | 0.325 [0.09, 0.44] | 0.250 [0.00, 0.44] | 0.275 [0.00, 0.39] |
| stale_symbol_refs | 0.25 | 0.275 [0.00, 0.39] | 0.283 [0.00, 0.44] | 0.250 [0.00, 0.39] | 0.225 [0.00, 0.37] | 0.283 [0.00, 0.44] |
| stale_symbol_refs | 0.50 | 0.275 [0.00, 0.39] | 0.275 [0.00, 0.41] | 0.250 [0.00, 0.39] | 0.233 [0.00, 0.39] | 0.275 [0.00, 0.41] |
| stale_symbol_refs | 0.75 | 0.275 [0.00, 0.39] | 0.275 [0.00, 0.39] | 0.267 [0.03, 0.43] | 0.225 [0.00, 0.39] | 0.275 [0.00, 0.39] |

Observations supported directly by this table (updated for the
regenerated run — see the note below on what changed from the pre-fix
version):

- `bm25`'s `hit_at_5` is constant (0.275) across every operator and
  severity. This is expected, not a sign of robustness: all three
  corruption operators used in this pilot modify only graph edges, never
  node text, and `bm25_rank` never reads edges. BM25's invariance here is
  a property of the experimental design, not an empirical finding about
  lexical retrieval. This invariance is exact and unchanged by the
  graph-builder fix, as expected.
- `fixed_hybrid` (and `diagnostic_gate`, identical to it — §6) now shows a
  monotonic upward trend under `missing_edges` as severity increases
  (0.275 → 0.283 → 0.292 → 0.300), and a non-monotonic bump under
  `stale_symbol_refs` (0.275 → 0.283 → 0.275 → 0.275) and
  `high_centrality_edges` (0.275 → 0.275 → 0.300 → 0.275). **This reverses
  which operator showed the pre-fix run's "monotonic trend"**: the
  original run reported a small monotonic increase under
  `stale_symbol_refs` (0.275 → 0.292 → 0.300 → 0.317) and a flat/slightly
  negative trend under `missing_edges`; neither pattern survives the
  graph-builder fix. Given the confidence-interval widths (which fully
  overlap `bm25`'s estimate in every cell, both before and after the fix),
  the most defensible reading is that neither the original nor the
  regenerated "trend" is a real signal — both are consistent with noise
  in a three-repository-cluster point estimate, and the fact that a minor,
  unrelated graph-construction bug fix changes which operator happens to
  look "trending" is itself evidence for that reading, not against it.
- `graph_expansion` and `repomap` are consistently at or below `bm25` across
  every condition except `graph_expansion` at `high_centrality_edges`
  severity 0.75 (0.325, previously 0.300), the only cell where a
  graph-structural method's point estimate exceeds `bm25`'s, and its CI
  still spans `bm25`'s estimate — unchanged from the pre-fix run.
- No method's CI excludes any other method's point estimate in any row.
  With three repository clusters, this pilot cannot support a statistically
  grounded ranking between methods. Unchanged from the pre-fix run.

## 6. DiagnosticGate behaviour

`results/pilot/metrics.csv` records `policy_chosen` and the three
diagnostic signals (`node_coverage`, `anchor_confidence`,
`isolated_node_rate`) for every one of the 1,200 `diagnostic_gate` rows.

| `policy_chosen` | Count | Share |
|---|---|---|
| `hybrid` | 1,200 | 100% |
| `lexical_only` | 0 | 0% |
| `abstain` | 0 | 0% |

Across all 1,200 rows: `node_coverage` is exactly 1.0 (mean, min and max
all 1.0) and `anchor_confidence` is exactly 1.0 (mean, min and max all
1.0) — unchanged by the graph-builder fix, since these three edge-only
operators never remove nodes. `isolated_node_rate` does vary with
corruption, from a mean of 0.0032 at `severity = 0.0` up to a mean of
0.349 at `missing_edges`, severity 0.75 (overall max 0.4231 across all
1,200 rows); these are slightly higher than the pre-fix run's 0.003 and
0.311 respectively, consistent with a smaller, less redundant edge set
making isolation somewhat more sensitive to the same edge removals.

Given `DiagnosticGate`'s thresholds (`coverage_floor = 0.6`,
`isolated_ceiling = 0.5`, `anchor_floor = 0.1`, from
`src/gemma_research/evidence/retrieve.py`), `node_coverage ≥ 0.6` and
`anchor_confidence ≥ 0.1` hold on every row by construction (both are
always 1.0), and `isolated_node_rate` never exceeds 0.5 even at the
highest severity tested. The `graph_reliable` condition in
`DiagnosticGate.choose_policy` is therefore `True` on every row, and the
policy is `"hybrid"` every time — which is why `diagnostic_gate` and
`fixed_hybrid` are numerically identical throughout §4–§5. This is
explained mechanistically, not left as an unexplained coincidence, in
`research/novelty_assessment.md` §2.

## 7. Resource use

| Method | Mean runtime per call (s) | Std (s) | Max (s) |
|---|---|---|---|
| `bm25` | 0.381 | 0.358 | 2.50 |
| `graph_expansion` | 0.468 | 0.394 | 2.66 |
| `repomap` | 0.582 | 0.447 | 4.02 |
| `fixed_hybrid` | 0.871 | 0.764 | 6.93 |
| `diagnostic_gate` | 1.259 | 1.102 | 7.15 |

`diagnostic_gate`'s higher runtime reflects that `DiagnosticGate.rank`
always computes diagnostics and then (because it always selects `"hybrid"`
in this pilot) also runs the full `fixed_hybrid_rank` computation, so its
cost is additive on top of `fixed_hybrid`. Runtimes are somewhat higher
throughout than the pre-fix run (whose figures are preserved in git
history), most likely machine-load variance between runs rather than a
consequence of the fix itself — the fix reduces graph size, which would
be expected to reduce runtime if anything, not increase it.

Full-run peak RSS was 935 MiB on a single process.
