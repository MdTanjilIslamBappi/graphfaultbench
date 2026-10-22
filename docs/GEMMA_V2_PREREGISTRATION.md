# Gemma 4 E2B reranking, v2 — pre-registration (2026-10-22, before any v2 run)

**Why v2.** The v1 demo (15 tasks, 3 repositories, 30 calls) parsed on average 3.1 of 5 ids and left hit@5 unchanged. v2 changes only output handling: candidates are numbered and decoding is constrained by a GBNF grammar to five candidate numbers. Prompt wording otherwise, candidate pool (top-15 of `fixed_hybrid`), model (Gemma 4 E2B Q4_0 GGUF, sha256 in `manifests/gemma4_manifest.json`), generation parameters (temperature 0.0, top_p 0.95, top_k 64, max_tokens 200) are unchanged. The v1 sample overlaps v2's tasks, so v2 is a reliability fix evaluated on a superset, not a held-out test of the prompt.

**Sample (fixed in advance).** All 54 pilot evaluation tasks (six repositories), severities 0.0 and 0.5 (`missing_edges`, seed 1): 108 calls. Resumable JSONL at `results/gemma_v2/calls.jsonl`.

**Measures.** Primary: hit@5 of Gemma's top-5 vs `fixed_hybrid` top-5 on the same rows (paired difference, repository-clustered bootstrap). Secondary: parse validity (calls with 5 valid distinct ids), candidate-pool recall (gold in top-15, the ceiling for any reranker), MRR, latency, tokens. CPU only; no GPU, no API.

**Interpretation rule.** Any result is reported. With 54 tasks in 6 clusters the study can detect only large effects; a null result is "no evidence of a difference", not evidence of none. No Gemma-specific claim unless the paired CI excludes zero.
