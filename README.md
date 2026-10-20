# GraphFaultBench — Gemma 4 Developer Agent Paper Track entry

Solo Kaggle Paper Track entry (https://www.kaggle.com/competitions/gemma-4-developer-agent-paper).
This repository holds **GraphFaultBench**: a benchmark harness that applies deterministic,
severity-graduated corruption operators to statically-built code dependency graphs and scores
retrieval/localisation policies — including an adaptive fallback gate and a Gemma 4 E2B reranking
demonstration — against real Loc-Bench V1 issue-localisation tasks. See `paper/manuscript.md` for
the full write-up and `paper/kaggle_writeup.md` for the condensed competition submission.

## What is and is not true right now

- A tested, real Python evaluation framework (`src/gemma_research/`): typed graph/task data
  structures, five deterministic graph-corruption operators with auditable manifests, five
  retrieval/localisation baselines (`bm25`, `graph_expansion`, `fixed_hybrid`, `repomap`,
  `DiagnosticGate`), Hit@k/MRR/strict-accuracy/clustered-bootstrap-CI metrics, and a Gemma 4 E2B
  reranking module (`src/gemma_research/evidence/gemma_rerank.py`).
- Run end-to-end on **real** Loc-Bench V1 tasks against **real**, commit-pinned GitHub repository
  snapshots (not a synthetic fixture): a pre-registered pilot (`configs/pilot_a.yaml`) across
  `python/mypy`, `dask/dask` and `PrefectHQ/prefect`, subsequently widened to six repositories
  (adding `numpy/numpy`, `scipy/scipy`, `aio-libs/aiohttp`) to narrow the bootstrap confidence
  intervals. Real, non-invented results are committed under `results/` and
  `reports/pilot_results.md`. `experiments/pilot_a/run_framework_validation.py`'s
  synthetic-fixture run (`results/framework_validation/`) remains from early development as a
  harness smoke test, not as this project's evidence.
- A separate, smaller secondary-evidence demonstration reranks a fixed candidate pool with a real
  Gemma 4 E2B checkpoint (4-bit GGUF, local CPU inference) — see
  `research/gemma4_downstream_go_no_go.md` and `results/gemma_downstream_demo/`.
- The headline empirical finding is a **negative/mixed result, reported honestly**: across the
  methods tested, no adaptive fallback policy evaluated here is supported as a validated
  reliability mechanism. The benchmark and corruption-operator harness itself — reusable
  independently of that specific finding — is this project's primary contribution.

## Quick start

```bash
uv sync --extra dev
uv run pytest -q                                     # 66 tests, CPU-only, <1s
uv run python experiments/pilot_a/run_real_pilot.py  # the real pilot (~70-110 min on 3 repos)
```

## Layout

- `src/gemma_research/data/` — typed `Node`/`Edge`/`CodeGraph`/`LocalizationTask`,
  `graph_builder.py` (static-analysis graph construction), `loc_bench_tasks.py`,
  `repo_source.py` (cached GitHub snapshot fetching).
- `src/gemma_research/evidence/` — `perturb.py` (deterministic corruption operators),
  `retrieve.py` (BM25/graph-expansion/fixed-hybrid/repomap/`DiagnosticGate` baselines),
  `gemma_rerank.py` (Gemma 4 E2B reranking over a fixed candidate pool).
- `src/gemma_research/metrics/` — `scoring.py` (Hit@k, strict accuracy, MRR, clustered bootstrap CI).
- `experiments/pilot_a/` — the pilot's experiment scripts.
- `paper/` — `manuscript.md` (full write-up), `kaggle_writeup.md` (condensed, ≤3,000-word
  submission), `references.bib`, `academic_style_guide.md`.
- `research/` — `compliance.md` (verified competition rules), `novelty_assessment.md`,
  `novelty_matrix.csv`, `limitations.md`, and the phase-specific validation notes.
- `manifests/` — sha256 + provenance records for third-party data/model downloads (see "Data and
  licensing" below) — never the data itself.
- `results/` — committed metrics, run manifests and graph/resolution reports for every experiment
  reported in the paper. These are derived numbers only (hit/miss rates, confidence intervals,
  task/commit identifiers); no Loc-Bench problem statements or patches are stored here.

## Data and licensing

- **Loc-Bench V1** (Hugging Face `czlll/Loc-Bench_V1`) states no explicit licence on its dataset
  card, only a citation request. This repository therefore never redistributes the dataset itself
  — only sha256 + provenance manifests (`manifests/data_manifest.json`) and derived metrics
  computed from it. To reproduce, fetch the dataset yourself from its original source.
- **Gemma 4** (`google/gemma-4`, E2B/Q4_0 GGUF checkpoint used for the secondary-evidence
  reranking demo) is released under Apache License 2.0 — see `research/gemma4_downstream_go_no_go.md`
  for the licence-verification note. The checkpoint itself is not redistributed here; fetch it from
  Kaggle Models or Hugging Face.
- **This repository's own code and text** are licensed under Apache License 2.0 (`LICENSE`),
  matching the licence the competition names for a winning submission's code
  (OSI-approved, no restriction on commercial use).

## Provenance note

This is a curated subset of a larger private development repository. Internal process-tracking
material — a dated decision log, an editorial QA pass log, a Kaggle-rules compliance checklist
used to track submission logistics, and internal decision-gate memos — is not included here,
since it documents the development workflow rather than the research artefact itself. Every
result, code path and data manifest included in this repository is an unmodified copy of what
produced the submitted Writeup and manuscript; nothing here has been altered for public
presentation beyond removing those internal cross-references.
