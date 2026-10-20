# Limitations — GraphFaultBench real-data pilot

Compiled after the pilot run completed (`reports/pilot_results.md`),
covering both limitations anticipated before the run and ones only visible
once real results existed. Nothing here is hypothetical where a concrete
number is available; where a limitation is a design property rather than
a measured one, it is labelled as such.

## 1. Statistical power

Only `n_repos = 3` repository clusters were used, because the clustered
bootstrap (`bootstrap_ci_clustered`) resamples whole repositories, not
individual tasks, to avoid treating correlated within-repository tasks as
independent evidence. With three clusters, every 95% confidence interval
in `results/pilot/summary.json` is wide (commonly spanning from 0.0 to
0.33–0.46), and no method's interval excludes any other method's point
estimate in any corruption condition. This pilot can report point
estimates and qualitative trends but cannot support a statistically
grounded ranking between retrieval methods. A larger repository sample is
the direct remedy, and is the main lever available before the 12 November
deadline if a stronger statistical claim is wanted.

## 2. Corruption operators perturb edges only, not nodes or text

All three corruption operators used (`missing_edges`,
`high_centrality_edges`, `stale_symbol_refs`) modify only the edge set of
the graph; none removes nodes or alters node text. Two consequences,
both visible directly in the pilot's own data:

- `bm25_rank`, which never reads edges, is exactly invariant to all three
  operators at all severities (`hit_at_5 = 0.275` in every row). This is
  a property of the experimental design, not a finding about lexical
  retrieval's robustness, and should not be presented as the latter.
- Two of `DiagnosticGate`'s three diagnostic signals (`node_coverage`,
  `anchor_confidence`) are structurally insensitive to this class of
  corruption and were observed at exactly 1.0 throughout the pilot — see
  `research/novelty_assessment.md` §2 for the full mechanistic account.

A node-removal or text-corruption operator was scoped but not implemented
in this pilot; its absence is the direct cause of the gate's observed
non-differentiation and should be treated as the first methodological
addition if the gate's design is revisited.

## 3. Heuristic, name-based call-graph construction

`build_graph_from_source` resolves `obj.method()`-style calls by matching
the call's unqualified name against candidate nodes, preferring
same-file matches and falling back to a deterministic repository-wide
pick. This is documented in `graph_builder.py`'s module docstring as a
heuristic, not a type-aware resolver. The pilot's own `graph_reports.json`
shows the resulting unresolved-call rate is substantial: roughly 33% for
`python/mypy`, 45–48% for `dask/dask`, and 40–48% for `PrefectHQ/prefect`
(unresolved calls divided by attempted calls, computed directly from the
`n_edges`/`n_unresolved_calls` fields). This heuristic will also produce
some false positive edges (a call resolved to the wrong same-named
method), which are not separately counted. The resulting graphs are
real and reproducible, but their edge set should not be treated as a
ground-truth call graph.

## 4. Only `.py` files are parsed; only same-snapshot imports are followed

Import resolution only adds an edge when an `import`/`from import`
statement resolves to a file inside the same repository snapshot;
external-package imports (the majority of imports in most real Python
code) are not represented. No file across any of the 41 commits in this
pilot failed to parse (`n_files_skipped = 0` throughout), so this
limitation did not cause any data loss in this run, but it does mean the
import-edge subset of the graph under-represents real inter-module
coupling for any repository with substantial third-party dependency use.

## 5. Query text is `problem_statement` only

Per the directive's leakage-control requirement, no retrieval method is
given `hints_text`, `patch`, or `test_patch` content. This is a deliberate
methodological choice to prevent trivial leakage, not a limitation to be
fixed; it is recorded here because it means the measured hit rates
reflect a harder, leakage-free setting and should not be compared directly
against any prior work that does use hint text or patch content as part
of the query.

## 6. Repository and task selection was constrained by practicality, not sampling theory

The three repositories (`python/mypy`, `dask/dask`, `PrefectHQ/prefect`)
were selected from Loc-Bench V1's 165 repositories for having
fully-populated gold labels and a manageable per-commit tarball size (see
`research/decision_log.md`), not by random or stratified sampling. The 40
evaluation tasks and 0 exclusions reported in §2 of
`reports/pilot_results.md` are a property of these three repositories and
should not be assumed to generalise to the full 165-repository, 560-row
Loc-Bench V1 population without further sampling.

## 7. Dev split exists but is unused

20% of tasks per commit (`is_dev_split`, deterministic sha256-based) were
held out as a dev split and excluded from every metric reported in
`reports/pilot_results.md`. This pilot does not tune any threshold on
them; they exist for future threshold-tuning work (e.g. the
`isolated_ceiling` revision discussed in `research/novelty_assessment.md`
§3) and are reported as a count (7 tasks) for transparency, not used.

## 8. `repomap_rank` is a reimplementation, not the published tool

`repomap_rank` is this project's own personalised-PageRank reimplementation
of the idea behind aider's RepoMap, built from `networkx.pagerank` seeded
by BM25 lexical anchors. It is not aider's own code and its performance
figures in this pilot (`reports/pilot_results.md` §4–§5) should not be
read as a measurement of the original tool.

## 9. Organiser dataset not used

Per directive §6, the organiser's own graph/embedding bundle (the ~23 GB
Kaggle download) was not used; all graphs in this pilot were built by this
project's own static-analysis pipeline from public GitHub source. This
was an explicit, approved scope decision, not an oversight, but it means
this pilot cannot speak to how the proposed methods would perform against
the organiser-provided graph representation specifically.

## 10. Single pilot run, no repeated-run variance estimate

The pilot was run once (not repeated across independent process runs);
seed variation (`seeds = [1, 2, 3]`) covers randomness inside the
corruption operators, but not variance arising from, for example, network
conditions during repository download. Given the full pipeline is
otherwise deterministic (static analysis, no stochastic model inference),
this is judged a low-risk gap, not a blocking one.

## 11. Duplicate node identifiers — fixed, and Phases 2–4 regenerated with the fix

`build_graph_from_source` could previously emit more than one `Node`
object sharing the same `node_id` (dominant cause: `@typing.overload`
stub signatures; rarer cause: a genuine same-name redefinition later in a
file), affecting roughly 0.2–0.7% of nodes per commit. This was first
noticed in Phase 3 (`research/node_removal_operator.md` §7) and confirmed
again in Phase 4. It was fixed on 2026-10-17 — see
`research/decision_log.md`'s entry of that date for the root-cause
investigation and the fix. `results/pilot/`, `results/node_omission_dev/`
and `results/coverage_floor_eval/` were then regenerated with the fix
applied on 2026-10-18/19 (`research/decision_log.md`'s regeneration
entry), replacing the original, pre-fix numbers in place; the pre-fix
numbers remain available in git history. Phase 2's and Phase 3's headline
comparative findings were confirmed unchanged by the regeneration
(`DiagnosticGate`/`fixed_hybrid` still tie exactly on 1,200/1,200 rows;
the gate still switches on exactly 42/84 dev-split rows). Phase 4's
headline *conclusion* (no measurable accuracy benefit from the gate's
switch) is also unchanged, but one supporting detail is not: at severity
0.75, the fix changes which task×seed rows are gold-visible, which
reverses the point-estimate direction between `fixed_hybrid` and
`bm25`/`diagnostic_gate` at that one severity (`research/coverage_floor_eval_validation.md`
§5). This is now treated as informative in its own right — a
point-estimate "finding" that flips under an unrelated, correctness-only
fix was likely never a reliable signal — rather than as evidence the
fix introduced a problem.
