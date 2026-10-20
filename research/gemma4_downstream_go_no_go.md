# Gemma 4 downstream demonstration — go/no-go analysis (pulled forward from 29 Oct–4 Nov)

**Status: analysis complete, decision pending user confirmation.** No Gemma weights have been
downloaded and no inference has been run. This document is the feasibility research requested by
the user ("go for Candidate A's Gemma 4 downstream go/no-go early"), produced ahead of the
29 Oct–4 Nov timeline slot where `docs/human_actions.md` item 3 originally scheduled this
decision. Nothing here commits to running anything; see "What this analysis does not do" at the
end.

## 1. What is actually being decided

Both governing documents describe this as **optional secondary evidence**, not a required
component:

> "Keep the method simple enough to explain precisely and test without Gemma 4. If able, add
> **one small, properly controlled Gemma 4 downstream demonstration** on legally and technically
> permitted accelerator resources to show relevance; label that as secondary evidence and report
> full generation parameters. Do **not** require L4x4 or prohibitively expensive training for a
> paper-track MVP." — `Gemma4_Paper_Track_Competition_Playbook.md:134`

A separate internal planning note made the same requirement from a different angle: test a small
stratified sample with an accessible Gemma 4 model if feasible, and do not substitute another
model's output for a genuine Gemma run.

So the question is narrow: is there an **accessible** Gemma 4 model and a **legally/technically
permitted**, cheap way to run a **small stratified sample** through it, to show the benchmark's
corruption-and-retrieval setup is relevant to an actual Gemma-driven localisation agent — reported
honestly as secondary evidence, not as a headline finding.

## 2. Compute feasibility audit (this machine)

Verified directly, not assumed:

- **GPU:** none. `lspci` shows only a VMware SVGA II virtual display adapter; `nvidia-smi` is not
  present. No CUDA/ROCm path exists on this machine.
- **RAM:** 15 GiB total, ~10 GiB available at audit time (`free -h`).
- **CPU:** 12 cores.
- **Disk:** 29 GiB free (`df -h /`).
- **No local Gemma checkpoint, no Ollama, no Hugging Face cache** (`~/.cache/huggingface/hub` does
  not exist) — a from-scratch setup either way.

## 3. What "an accessible Gemma 4 model" actually means in practice

Checked `ai.google.dev/gemma/docs/core` directly (not inferred from memory) and cross-referenced
against the `google/gemma-4` model's published instance file sizes on Kaggle Models (via the
now-working API token, metadata listing only — no files downloaded):

Gemma 4 is a **five-size family**, not one model: E2B, E4B, 12B, 26B-A4B (MoE), and 31B (dense).
Approximate weight-loading memory (GPU/TPU figures, +20% overhead; CPU/llama.cpp-style runtimes
are comparable for static weights, plus KV cache):

| Variant | BF16 | 8-bit (SFP8) | 4-bit (Q4_0) | Mobile (LiteRT-LM, text-only) |
|---|---|---|---|---|
| E2B (2B effective) | 11.4 GB | 5.7 GB | **2.9 GB** | 0.84 GB |
| E4B (4B effective) | 17.9 GB | 8.9 GB | 4.5 GB | 2.2 GB |
| 12B | 26.7 GB | 13.4 GB | 6.7 GB | – |
| 26B-A4B (MoE, 4B active/token) | 57.7 GB | 28.8 GB | 14.4 GB | – |
| 31B (dense) | 69.9 GB | 34.9 GB | 17.5 GB | – |

The 26B-A4B MoE variant must still load all 26B parameters (only the *compute per token* is
reduced to ~4B), so its memory footprint is close to a dense 26B model regardless of quantization
— this is the variant that would be genuinely infeasible here even at 4-bit (14.4 GB against
~10 GiB available RAM and no GPU to offload to).

**The E2B variant at 4-bit quantization (~2.9 GB) is the one that actually fits this machine's
constraints** — well within 29 GB free disk and plausible within 15 GB RAM for CPU-only inference
via a GGUF-format runtime (Google publishes official Quantization-Aware Training checkpoints in
GGUF, among other formats, specifically for this kind of on-CPU/edge use). This is consistent with
the playbook's "do not require L4x4 or prohibitively expensive training" instruction — E2B/Q4_0 is
the one configuration that matches "small, properly controlled" without any paid or cloud
accelerator.

Corroborating evidence from `kaggle models instances list google/gemma-4`: alongside several very
large instances (51.6 GB, 62.6 GB — consistent with BF16/near-BF16 dense 31B and 26B-A4B weights),
there are several small instances in the 180 MB–2.5 GB range, consistent with quantized E2B/E4B
variants and/or component-only artefacts (tokenizer, vision tower). The CLI's instance listing
does not surface variation slugs/framework labels, so this is corroborating, not a substitute for
confirming the exact variation before any download.

## 4. What this does NOT require

- **No GPU purchase or cloud accelerator session.** This removes the main risk the playbook and
  `docs/human_actions.md` item 3 originally flagged ("requires either local access to a Gemma 4
  checkpoint or an authorised Kaggle/other accelerator session") — a local, CPU-only, free path
  exists for the E2B variant specifically.
- **No fine-tuning.** Inference only, on a small stratified task sample, consistent with this
  project's standing rule against GPU dependencies/heavyweight orchestration "unless a real
  result demonstrates necessity" — this stays inside that boundary precisely because it avoids
  both GPU dependency and heavyweight orchestration.
- **No expensive API calls.** A local checkpoint avoids per-token API billing entirely.

## 5. What it DOES still require, and what remains open

1. **A one-time file download** (the quantized E2B checkpoint, likely 1–3 GB depending on exact
   variation/format chosen). Per this session's own operating rules, any file download requires
   explicit permission (filename, source, exact size) before it happens — not yet requested, and
   not performed as part of this analysis.
2. **Gemma's usage licence.** Google's Gemma models are typically released under the Gemma Terms
   of Use (a specific, permissive-but-not-open-source licence with use restrictions), separate
   from Kaggle's own competition rules. This has not yet been checked against this specific
   `google/gemma-4` Kaggle listing's licence text. Licence/eligibility
   judgement calls are an explicit-approval item in this project — this would need to be confirmed (and the
   licence terms actually read) before any download, not assumed permissive by default.
3. **A CPU inference runtime.** Nothing is installed yet (no `llama.cpp`, no GGUF Python bindings,
   no `transformers`+`bitsandbytes` CPU path). Setting this up is itself non-trivial dev work —
   plausibly an hour or two, not heavyweight, but real work against a 23-day remaining budget.
4. **A small stratified task sample design.** The contingency document says "test a small
   stratified sample" but does not specify size; this project's own Phase 2–4 pilots used 40 eval
   tasks across 3 repositories — a Gemma downstream demonstration would need its own small
   (plausibly 10–20 task), clearly-labelled sample, separate from the frozen Phase 2–4 evaluation
   split, to avoid any appearance of post-hoc cherry-picking against already-reported numbers.
5. **Manuscript/Writeup impact.** Neither `paper/manuscript.md` nor `paper/kaggle_writeup.md`
   currently mentions a Gemma 4 downstream demonstration anywhere (confirmed by direct grep) — the
   current thesis (benchmark/harness as primary contribution, `DiagnosticGate` reported as a
   genuine negative/non-differentiating result) does not depend on it and was already carried
   through five editorial reviews and two independent-perspective passes without it. Adding a new
   experimental section this late would require at least a partial re-review (Review C technical
   accuracy, Review D research integrity) and would use some of `kaggle_writeup.md`'s remaining
   word-count margin (currently 2,821/3,000 words — only ~180 words of headroom, which a
   "secondary evidence" paragraph with generation parameters would likely consume most or all of).

## 6a. Licence check (performed 2026-10-20, in response to the user's follow-up)

Checked directly against Google's own pages, not assumed from training-data memory (Gemma 4
postdates the knowledge cutoff) or from third-party summaries alone, though one third-party guide
(`vorplabs.com/models/gemma-license`, surfaced by search) said the same thing independently:

1. `ai.google.dev/gemma/terms` — Google's custom "Gemma Terms of Use" document — states its own
   scope explicitly: "The terms below apply to Gemma models listed in the Appendix at bottom of
   this page," and separately: **"For Gemma 4 terms, see the Gemma 4 license"**, linking out. The
   Appendix enumerates Gemma 1 through Gemma 3n and variants; **Gemma 4 is not listed in it.** This
   is the strongest single signal: Google's own custom-terms document explicitly carves Gemma 4
   out of its own scope.
2. Following that link leads to `ai.google.dev/gemma/apache_2` (marked **deprecated**, redirecting
   to `gemma.ai`) and then to `gemma.ai/resources/apache-2/`, both of which reproduce the full text
   of the **Apache License 2.0**, and both of which are labelled "Gemma 4 license" in the site's
   Legal navigation.
3. The separate Gemma Prohibited Use Policy (`gemma.ai/resources/prohibited-use/`) does not name
   Gemma 4 anywhere in its text and carries a "Last modified: February 21, 2024" date, predating
   Gemma 4's 2 April 2026 release — it was written for the custom-terms model family, and nothing
   on Google's pages states it is additionally layered on top of the Apache-2.0-licensed Gemma 4.

**Conclusion, stated with appropriate confidence rather than certainty:** Gemma 4 appears to be
released under plain Apache License 2.0, distinct from every earlier Gemma generation's custom
Terms of Use + Prohibited Use Policy combination. No single page gives one unambiguous sentence
such as "Gemma 4 is licensed solely under Apache 2.0 with no additional restrictions" — this is
inferred from consistent navigation labelling and explicit scope exclusion across three official
pages, corroborated by one independent third-party source. If this holds, it is **more permissive**
than what this project already navigates for Loc-Bench V1 (unstated licence, redistribution
caution) — Apache 2.0 permits research use, modification, and redistribution with attribution and
a licence/NOTICE copy, no prohibited-use enforcement clause. Consistent with this project's rule
against treating licence determinations as settled without being explicit about verification depth, this
is reported as "high-confidence research finding," not as a closed legal determination — I should
treat this the same way I treated self-certification elsewhere in this project: the final call on
relying on it is mine to make, not something this analysis settles on its own.

## 6. Recommendation

**Conditional go, narrowly scoped to the E2B/Q4_0 local-CPU path. The licence objection is now
resolved (§6a, high confidence: Apache 2.0, no prohibited-use overlay). One explicit confirmation
remains before any action is taken:**

1. Permission to download the specific E2B quantized checkpoint file (exact filename/variation
   and size to be confirmed and stated before downloading, per this session's own rules).
2. Confirmation that spending project time (estimated: a few hours total — runtime setup,
   10–20-task stratified sample run, write-up of a short secondary-evidence paragraph) on this is
   worth the corresponding word-count and editorial-review cost, given the manuscript is already
   complete and independently reviewed without it, and 23 days remain to the 12 Nov deadline.

**Why conditional rather than a clean go:** the original blocker (needing GPU/cloud access) has
turned out to be avoidable via the E2B variant — but that finding does not by itself establish
that spending remaining time on an *optional* addition is the best use of it against other open
items (e.g. `docs/human_actions.md` items 1's residual self-certification, item 4's licence
caveat, or the "widen the repository sample" optional item already logged in
`paper/submission_checklist.md`). This is a scope/priority call, not a pure feasibility call, so
it is reported back rather than decided unilaterally.

**Why not a no-go:** unlike the originally-assumed scenario (requiring a ~52 GB 26B-A4B checkpoint
and either a GPU or paid cloud accelerator), the E2B/Q4_0 path is genuinely cheap, free, and
fits this machine's actual resources — the playbook's "small, properly controlled... do not
require L4x4 or prohibitively expensive" framing is a closer match to this specific configuration
than to any larger Gemma 4 variant.

## 7. Smoke test (performed 2026-10-20, after the user's go-ahead)

User approved proceeding ("Go ahead"), and separately approved the specific file download
(`gemma-4-E2B_q4_0-it.gguf`, 3.35 GB, Apache 2.0) after being shown filename/source/size, per this
session's own rules. What was actually done, with real output:

1. Downloaded the file via `kagglehub.model_download('google/gemma-4/gguf/gemma-4-e2b-it-qat-q4_0-gguf', path='gemma-4-E2B_q4_0-it.gguf')`
   into `manifests/raw_data/gemma4/` (gitignored, matching the existing Loc-Bench V1 provenance
   pattern). Verified size (3,349,514,112 bytes) and sha256
   (`3646b4c147cd235a44d91df1546d3b7d8e29b547dbe4e1f80856419aa455e6fd`), recorded in
   `manifests/gemma4_manifest.json`. 26 GiB disk remained free afterwards.
2. Installed `llama-cpp-python` 0.3.36 as a project dependency, from the maintainers' prebuilt CPU
   wheel index (`https://abetlen.github.io/llama-cpp-python/whl/cpu`) rather than compiling from
   source — this machine has no C/C++ compiler installed, and installing one system-wide would
   have been a more invasive, separately-worth-confirming change; the prebuilt-wheel route avoided
   that entirely.
3. **Smoke test 1** (trivial prompt): model loaded in 4.9 s, answered a one-word instruction
   correctly in 1.4 s. Confirms the full chain — download, load, CPU inference — works end to end
   on this exact machine.
4. **Smoke test 2** (realistic prompt size): a synthetic localisation-style prompt (~1,252 prompt
   tokens: issue text + 60 candidate file paths, asking for the top 5) completed in 82.3 s,
   producing a syntactically valid 5-file answer. The candidate files in this test were
   deliberately generic placeholders with no real connection to the issue text, so the answer's
   content (a simple sequential pick) is not informative about model quality — this test measured
   **throughput, not accuracy**. Observed completion-token rate ≈0.72 tokens/s; most of the 82 s is
   prompt processing at roughly 1,250 tokens in ~75 s (~17 tokens/s), consistent with an
   unaccelerated CPU BLAS backend on a 2B-class model.

**Planning implication:** at this throughput, a real stratified sample of 10–20 tasks (comparable
prompt sizes to real Loc-Bench issues + candidate lists) would take roughly 15–45 minutes of raw
inference time — well inside the "a few hours total" estimate in §6, and dominated by prompt
processing rather than generation, so keeping candidate-list/context size deliberately bounded
matters more than trimming `max_tokens`.

**Not yet done:** the actual stratified sample design (task selection, integration with the
existing Loc-Bench/graph-corruption harness, a real accuracy comparison against the Phase 2–4
baselines) and the manuscript/Writeup edit. Both are reported back to the user before proceeding,
consistent with this document's existing distinction between "feasibility confirmed" and "worth
building."

## 8. Stratified-sample demonstration (performed 2026-10-20, after "go ahead, build steps 1-3")

Built and ran `experiments/pilot_a/run_gemma_downstream_demo.py` (reusing
`gemma_research.evidence.gemma_rerank` and the same repos/commits/graphs/`LocalizationTask`
definitions as the Phase 2 pilot). Design, exactly as pre-registered in this file's module
docstring before the run: 5 eval tasks per repo (15 total; python/mypy, dask/dask,
PrefectHQ/prefect), chosen by a fixed `random.Random(20261020).sample()` over the sorted eval
task-id list pooled across every commit a repo contributes to Loc-Bench V1 — not cherry-picked
after seeing results. Two severities only (0.0 healthy, 0.5 `missing_edges`, seed=1). Gemma 4 E2B
reranks `fixed_hybrid_rank`'s own top-15 candidate pool (not open-candidate retrieval). Generation
parameters exactly as declared in `gemma_rerank.GENERATION_PARAMS`: temperature=0.0 (a stated
deviation from Gemma's documented default of 1.0, for reproducibility), top_p=0.95, top_k=64,
max_tokens=200. 60 rows total (30 `fixed_hybrid` + 30 `gemma_e2b_rerank`), total wall time 2,302 s
(~38 minutes) on this machine. Raw model outputs, per-task metrics and the bootstrap summary are
committed under `results/gemma_downstream_demo/` (`raw_outputs.json`, `metrics.json`,
`summary.json`, `run_manifest.json`).

**Bug found and fixed before this run, recorded for the record:** an earlier version of the
sampling function (`_select_sample`) was called once per `base_commit` rather than once per repo.
Loc-Bench V1 splits each repo across many commits (dask/dask: 19, PrefectHQ/prefect: 16,
python/mypy: 6 — mostly ~1 eval task each), so per-commit sampling silently pulled nearly every
available task instead of a bounded, documented 5. Caught via a dry run before the real run
(confirmed: fixing it dropped a 1-task-per-repo dry run from 6 tasks for python/mypy alone down to
the expected 1). Fixed by pooling every commit's tasks for a repo before sampling once.

**Primary-metric result (Hit@5, the pre-registered primary metric, clustered bootstrap CI over
repo):**

| Condition | fixed_hybrid Hit@5 | gemma_e2b_rerank Hit@5 |
|---|---|---|
| severity 0.0 (healthy) | 0.267 [0.0, 0.6] | 0.267 [0.0, 0.6] |
| severity 0.5 (missing_edges) | 0.200 [0.0, 0.4] | 0.200 [0.0, 0.4] |

**Finding: no differentiation on Hit@5.** On every single one of the 30 task×severity
combinations, Gemma's reranked top-5 produced the identical Hit@5 outcome (0 or 1) as taking
`fixed_hybrid_rank`'s own top-5 from the same pool, at both severities. This matches, on an
independent secondary-evidence run, the same qualitative pattern already reported for the
`DiagnosticGate` method in the Phase 2–4 pilot (`research/novelty_assessment.md` §2): an added
layer on top of the lexical+graph baseline did not change which tasks were solved, on this small
sample. Given the small sample (15 tasks, 3 repo clusters), the wide bootstrap CIs mean this
cannot be read as strong evidence either way — it is reported as a consistent observation, not a
significance claim.

**Finer-grained ranking metrics (MRR, Hit@1, Hit@3) are NOT directly comparable here, and this
analysis flags that rather than reporting them as a straightforward "Gemma did worse" result.**
`fixed_hybrid`'s MRR is computed over its full graph-wide ranking, while `gemma_rerank` only
returns a ranking restricted to its 15-candidate pool (unranked candidates beyond that score 0.0).
When the gold node sits outside the top-15 pool, `fixed_hybrid` can still receive a small nonzero
MRR credit from its long tail (e.g. gold at rank 2,401 of a large graph gives MRR ≈ 0.0004), while
Gemma's pool-restricted ranking cannot ever represent that node at all, so its MRR for that task is
forced to 0 by construction — not by a worse ranking decision. This pattern explains the majority
of the 28/30 task×severity combinations where the two methods' MRR differed (see
`results/gemma_downstream_demo/metrics.json`). Two cases did show a genuine, comparable change
within the shared pool: `dask__dask-11605` (fixed_hybrid's rank-1 pick was gold; Gemma moved it to
a lower rank but it stayed in the top 5, so Hit@5 was unaffected) and `dask__dask-10750`
(fixed_hybrid had gold at rank 4–5; Gemma moved it into the top 3). Both directions occurred once
each in this small sample.

**Instruction-following / output-format observation.** The prompt asked for exactly 5 candidate
node ids, one per line, nothing else. Across the 30 calls, the number of ids this harness's parser
could validate against the candidate pool (`n_parsed_valid`) was: 5 in 10 calls, 4 in 5 calls, and
1 in 14 calls (1 call scored 2, 0 calls scored 3). Inspecting `raw_outputs.json` for the
`n_parsed_valid == 1` cases shows Gemma frequently did not produce a clean ranked list at all;
instead it echoed back one candidate's full description text (sometimes truncated mid-word by the
200-token cap), from which the parser's fallback regex could only recover the one node id embedded
in that text. This is a genuine instruction-following limitation of the E2B model at this
quantisation/prompt, distinct from a localisation-accuracy failure, and is reported as such rather
than folded into the accuracy numbers.

**Runtime.** Mean Gemma call latency: 62.9 s (range ~9–187 s, driven mostly by prompt length —
longer candidate-text snippets took longer). Mean `fixed_hybrid_rank` latency: 1.17 s. This
confirms §7's throughput-dominated-by-prompt-processing observation on real, non-synthetic prompts.

**What this does and does not show.** This is a small, secondary-evidence demonstration (15 tasks,
3 repos, one model, one prompt design, one reranking strategy), not a validated claim that LLM
reranking cannot help localisation in general. It shows, on this sample, that a direct
"rerank-the-same-pool" application of Gemma 4 E2B did not change which tasks were solved at the
competition's own primary metric, and surfaces a concrete instruction-following limitation that
would need addressing (e.g. structured output / constrained decoding) before a larger study could
even measure accuracy cleanly.

## What this analysis does not do

It does not download any file, install any inference runtime, accept any licence on the user's
behalf, or change `paper/manuscript.md` / `paper/kaggle_writeup.md`. It is feasibility research
only, reported back per this project's standing rule that licence judgement calls, non-trivial
time allocation, and changes to the novelty/evidence thesis all require explicit user approval.
