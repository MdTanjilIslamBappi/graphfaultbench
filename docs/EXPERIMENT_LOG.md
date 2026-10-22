# Experiment log (new entries, 2026-10-22 onward)

Earlier runs (pilot, node-omission dev, coverage-floor eval, weighted gate, Gemma demo) are recorded in the internal status log (withheld from this release) and the internal decision log (withheld from this release); commit `ce105c3` is the pre-audit code revision.

## E-00 Independent recomputation of pilot headline numbers
- Script: `scripts/validate_headline_claims.py` (stdlib only). Data: `results/pilot/metrics.csv` (sha of dataset in `run_manifest.json`).
- Outcome: all checked headline numbers reproduced (see the internal baseline audit (withheld from this release) §2). Status: complete.

## E-01 stale_rewire evaluation (previously unevaluated operator)
- Config: `configs/stale_rewire_eval.yaml` (identical to `configs/pilot_a.yaml` except `corruption_operators: [stale_rewire]`). Runner: `experiments/pilot_a/run_real_pilot.py` with `stale_rewire` added to `CORRUPTION_OPS`; no other code changed.
- Output: `results/stale_rewire_eval/`. Started 2026-10-22; complete (3,240 rows, 54 eval tasks, 1 exclusion, wall 10,104 s single process, peak RSS 1,229 MiB).
- Validation: healthy-control rows match the original pilot 810/810; gate chose `hybrid` 648/648. Results: bm25 / fixed_hybrid / gate hit@5 = 0.333 at all severities; graph_expansion 0.296 (sev 0) → 0.278 (0.75); repomap 0.278 → 0.284. Paired differences: `results/analysis/paired_differences_stale_rewire_eval.json`. Interpretation: no detectable degradation for the hybrid; descriptive only.
- Same repositories, cached commits, seeds, thresholds as the original pilot; nothing tuned.

## E-02 Paired differences with repository-clustered bootstrap
- Script: `scripts/paired_analysis.py`, seed 20261022, 5,000 resamples, unit = repository. Output: `results/analysis/paired_differences.json`. Status: complete for the original pilot.
- Observation: healthy-control fixed_hybrid − bm25 = 0.000 (CI [−0.056, 0.041]); under edge corruption no paired difference has a CI excluding zero except where the difference is exactly zero. Descriptive only (6 clusters).

## E-03 Repository-level holdout (pre-registered, `docs/HOLDOUT_PREREGISTRATION.md`)
- Six repositories absent from all earlier experiments: sqlglot, yt-dlp, Django, moto, sympy, matplotlib. Configs `configs/holdout_<name>.yaml`; outputs `results/holdout_<name>/`; code and `DiagnosticGate` thresholds identical to the pilot (no tuning); seed 1, severities 0/0.5/0.75, operators missing_edges, high_centrality_edges, stale_symbol_refs, stale_rewire; `dev_fraction: 0`.
- Tasks resolved: 95, exclusions 0 (Django 35, yt-dlp 27, sqlglot 15, moto 6, sympy 7, matplotlib 5). Rows: 4,275. Django wall time 20,096 s; the other five 506–720 s or longer (see logs).
- Analysis: `scripts/paired_analysis.py` on the six directories (seed 20261022, 5,000 resamples, unit = repository) -> `results/analysis/paired_differences_holdout_*.json`.
- Q1 (healthy fixed_hybrid − bm25): bm25 0.221 (21/95), fixed_hybrid 0.242 (23/95), difference +0.021, CI [0.000, 0.046]. The difference is entirely Django (12 vs 14 of 35); the other five repositories tie; yt-dlp (27) and moto (6) yield no hit for either method. graph_expansion 0.211, repomap 0.200.
- Q2: fixed_hybrid ranges 0.221–0.242 across all operators/severities (at most two tasks); graph_expansion falls to 0.189 under stale_rewire at 0.75 (two tasks, CI includes zero). No systematic decline.
- Q3: gate equals fixed_hybrid on 855/855 gate rows; `hybrid` chosen every time.
- Caveat: a five-repository preview (60 tasks) showed difference 0.000; adding Django moved it to +0.021. Interpreted as sensitivity to one repository, not as an effect. Descriptive only (6 clusters, one seed, edge-only operators).

## E-04 Gemma 4 E2B reranking v2 (pre-registered, `docs/GEMMA_V2_PREREGISTRATION.md`)
- Change from v1: candidates numbered, GBNF grammar constrains output to five candidate numbers (`gemma_rerank_indexed`); pool (top-15 of fixed_hybrid), model, generation parameters unchanged. Runner `experiments/pilot_a/run_gemma_v2.py`; calls in `results/gemma_v2/calls.jsonl`; analysis `scripts/gemma_v2_analysis.py` -> `results/gemma_v2/summary.json`.
- 54 pilot eval tasks x severities 0.0 and 0.5 (missing_edges, seed 1) = 108 calls; CPU only, no API.
- Validity: 83/108 calls returned five valid distinct ids (mean 4.769); v1 parsed 14/30 cleanly.
- hit@5: gemma 0.3981, fixed_hybrid 0.3333, bm25 0.3333. Paired gemma − fixed_hybrid +0.0648, CI [0.0357, 0.0968] (healthy +0.0926 [0.0465, 0.1458]; sev 0.5 +0.0370 [0.0000, 0.0789]). hit@1 0.3241 vs 0.2037; MRR 0.3559 vs 0.2630. Pool recall (top-15) 0.4167. Mean latency 24.58 s. Per-repo differences all >= 0 (aiohttp, numpy 0.000).
- Caveats: the two severities reuse the same tasks (not independent); the v1 sample overlapped these tasks, so this is a reliability fix and not a held-out test; six clusters; one model, one prompt. Pre-registered rule satisfied for the pooled and healthy strata (CI excludes zero); the severity-0.5 stratum is borderline (lower bound 0.000).
