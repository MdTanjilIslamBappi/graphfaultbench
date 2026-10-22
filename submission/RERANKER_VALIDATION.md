# Gemma 4 E2B reranker (v2): validation of the reported result

Audit date 2026-10-22. Code revision of the run: `59b7f5d` (runner, reranker, pre-registration committed together at 11:16 +0600, before the run; the run finished 19:24). Audit code: `scripts/audit_reranker.py` (rebuilds each pool and gold set from the commit-pinned source, re-parses `raw_output` with a separate parser, rescores; no model, no API). Output: `results/gemma_v2/audit.json`.

## Answers to the nine questions

1. **Scoring unit.** One model call = one (task, severity) pair; 108 calls = 54 tasks x 2 severities (0.0 and 0.5, `missing_edges`, seed 1). Hit is binary per call. The two severities of a task are not independent. Because every task contributes exactly two calls, the call-unit and task-unit paired estimates coincide (+0.0648, same CI); the effective sample is 54 tasks in 6 repository clusters.
2. **Invalid, duplicate, missing, out-of-pool ids.** The grammar forces five lines of numbers 1-15, so out-of-pool numbers cannot occur, but duplicates can. The parser (`parse_indexed_output`) keeps the first occurrence of each in-range number and drops repeats. All 25 sub-five outputs (valid count 4) were repeats, e.g. `1\n6\n9\n14\n1`; no call had fewer than four valid ids.
3. **Fallback.** Yes. The ranking is picked ids in output order followed by the unpicked pool ids in `fixed_hybrid` order. This is documented only in the code (v1 docstring and `gemma_rerank_indexed`) and not stated in the pre-registration text, a documentation gap. Only the Gemma arm uses it; the baselines use their own full rankings. Consequence: for a 4-valid call, Gemma's fifth slot is the best unpicked pool candidate.
4. **Same pool, gold, cases.** Verified. Pool = top-15 of `fixed_hybrid` on the same (possibly corrupted) graph; gold and tasks identical for gemma, fixed_hybrid and bm25 (rescoring reproduced all 108 stored fixed_hybrid hit@5 flags, 0 mismatches).
5. **Confidence interval.** Paired per-call differences, bootstrap resampling the six repositories (5,000 resamples, seed 20261022). Repository clustering absorbs task and severity dependence but six clusters is small, so the interval is descriptive. Exact sign test on tasks (post-hoc, descriptive): 6 tasks better, 0 worse, 48 tied, two-sided p = 0.031.
6. **Mean 4.77 valid ids.** Verified: 83 x 5 + 25 x 4 = 515; 515/108 = 4.769.
7. **Pool ceiling.** Same denominator (108 calls): gold is in the pool in 45/108 = 0.4167. Gemma hits 43 of those 45; fixed_hybrid 36.
8. **Fixed in advance?** Partly. Prompt, grammar, pool size, model, generation parameters, sample, primary comparator (`fixed_hybrid`), measures and interpretation rule were committed in `59b7f5d` before the run, and the run log shows one uninterrupted invocation with no traceback. Not pre-specified: the fallback rule (in code only), the bm25 comparison, and the well-formed/malformed split below. The v2 prompt was designed after seeing the v1 parse failure on an overlapping sample, so this is not a held-out test. I cannot rule out unlogged local smoke tests.
9. **Malformed outputs analysed separately.**

| stratum | calls | gemma hit@5 | fixed_hybrid hit@5 | gold in pool |
|---|---|---|---|---|
| five valid ids | 83 | 31 | 24 | 33 |
| four valid ids | 25 | 12 | 12 | 12 |
| all | 108 | 43 | 36 | 45 |

The entire improvement (+7 calls) comes from well-formed outputs; malformed calls are neutral, so the fallback does not manufacture the gain. Using the picked ids only (no fallback fill) gives the same 43, i.e. the fallback never contributes a hit.

## Recomputed values

| quantity | recomputed | stored |
|---|---|---|
| hit@5 gemma / fixed_hybrid | 43/108 = 0.398 / 36/108 = 0.333 | identical |
| hit@1 gemma / fixed_hybrid | 35/108 = 0.324 / 22/108 = 0.204 | identical |
| paired hit@5 | +0.0648, CI [0.0357, 0.0968] | identical |
| paired hit@1 | +0.1204, CI [0.0263, 0.2692] | not previously reported with CI |
| discordant calls | 7 gemma-only, 0 fixed_hybrid-only | |
| mismatches vs stored flags | 0 of 108 on hit@5, hit@1, pool recall, valid count | |

hit@5 of bm25 equals fixed_hybrid (0.333) in the stored records.

## Status and revisions

- Verified: all numbers in the manuscript's Gemma paragraph.
- Unverified / not established: generality beyond the 54 pilot tasks; behaviour with another prompt, model or pool size; any effect on a held-out set.
- Manuscript changes: counts added (43 v 36, 35 v 22), the fallback stated, malformed-call stratum reported, "close to the ceiling" replaced by "recovers 43 of 45", prompt revision after observing v1 disclosed, and the abstract marks the result as secondary and not held out.
- No new experiment is needed to settle the audit questions; a held-out replication (new repositories, same frozen prompt) would be the smallest useful extension, with acceptance criterion: paired CI excluding zero on at least 40 unseen tasks. Not run.

## Overlap with the earlier (v1) demonstration

All 15 v1 tasks (3 repositories: mypy, dask, prefect; 30 calls) are among the 54 v2 tasks (27.8% of tasks, 30 of 108 calls). Descriptive split of the v2 result (hit@5, gemma v fixed_hybrid, counts of calls): the 15 overlapping tasks 9 v 7 (two tasks gained); the 39 tasks the v1 demo never used 34 v 29 (four tasks gained, 78 calls, all six repositories represented). The gain therefore does not depend on the overlap, but the subsets are too small for separate inference. Source: the per-task demo output (not included in this release) task ids against `results/gemma_v2/calls.jsonl`.
