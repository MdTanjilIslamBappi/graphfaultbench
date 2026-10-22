# Licences, data access and exclusions

Checked 2026-10-22 from the sources named below. This is a record of what was found, not legal
advice.

## This repository
Apache-2.0 (`LICENSE`), chosen to match the licence the competition requires of a prize-winning
submission (Apache 2.0 is named in the competition rules).

## Dataset
| Item | Finding |
|---|---|
| Loc-Bench V1 (`czlll/Loc-Bench_V1`), introduced by LocAgent (arXiv:2503.09089; ACL 2025) | The Hugging Face dataset card states **no licence**, no terms of use and no redistribution statement; it asks users to cite the LocAgent paper. The LocAgent code repository declares Apache-2.0 for the code and says nothing about the dataset. The licence is therefore **unresolved**. |
| Handling here | No Loc-Bench rows, issue text or patches are included. Files carrying Loc-Bench task identifiers, gold-derived hit flags or per-task commit mappings are excluded (listed in the release manifest prepared for review) until the licence question is resolved. |

### Consequences of the unstated Loc-Bench V1 licence
- Re-checked 2026-10-22 through the Hugging Face API: the dataset record has `license: null`, no licence tag, no `LICENSE` file (files: `.gitattributes`, `README.md`, one parquet), and the card carries only the feature schema. The LocAgent repository's Apache-2.0 licence covers its code; its README states no terms for the dataset. **Permission to redistribute dataset-derived material could not be established.**
- Disposition: dataset content (rows, issue text, patches, labels), task identifiers, commit hashes, per-task gold flags, per-task rankings and node-level outputs are excluded. Retained are the authors' own per-condition aggregate statistics (method × operator × severity, per-repository summaries), which reproduce no dataset content. That retention is a judgement, not a determination of permission; if it is not accepted, `results/` (except `framework_validation/`) and the paper's tables would also have to be withheld.
- The absence of a licence is not a grant; this release therefore redistributes none of the dataset (rows, issue text, patches), nor per-task derivatives (task identifiers, gold-derived hit flags, commit mappings).
- Consequently the empirical results cannot be independently regenerated from this release, and per-task claims (for example which task a method solved) cannot be checked by readers without obtaining the dataset themselves.
- Aggregate counts, rates and intervals are published. Whether even these are permissible without a licence is not settled; if the dataset authors or an authoritative source later state terms, the release should be revisited.
- Earlier public commits of this repository contain some per-task files; they were not removed from history.

## Reproducibility statement
The public artefacts reproduce the **unit tests and the synthetic framework validation only** (the latter byte-identically in a clean environment). They do **not** reproduce the empirical results of the paper from raw inputs. Those results require Loc-Bench V1, the pinned repository snapshots and the Gemma GGUF obtained separately, and the end-to-end re-run has not been performed for this release. The aggregate files in `results/` are stored as-run records.

## Model
| Item | Finding |
|---|---|
| Upstream model | Gemma 4 (Google DeepMind). Google's licence page states that Gemma 4 is licensed under Apache 2.0 (https://ai.google.dev/gemma/docs/gemma_4_license, read 2026-10-22; the page is marked deprecated in favour of gemma.ai). The Kaggle model page for `google/gemma-4` shows the same licence. |
| File used | `gemma-4-E2B_q4_0-it.gguf` (3,349,514,112 bytes), sha256 `3646b4c147cd235a44d91df1546d3b7d8e29b547dbe4e1f80856419aa455e6fd`, taken from the Kaggle Models variation `google/gemma-4/gguf/gemma-4-e2b-it-qat-q4_0-gguf`, version 2, via `kagglehub` on 2026-10-20. The variation page lists the publisher as Google, a licence field of Apache 2.0, no description and no usage guide. It also lists a `README.md` and a vision-projector file (`gemma-4-E2B-it-mmproj.gguf`, not used). |
| GGUF header (read with a minimal parser; no code from the file was run) | GGUF v3, 43 key-value pairs; `general.architecture = gemma4`; `general.name = 2B_dequant_qat_it_hf`; `file_type = 2` (Q4_0). It contains **no** `general.license`, source-repository, converter or `quantized_by` field. |
| Variation `README.md` (read in full on Kaggle, 2026-10-22) | Front matter: `license: apache-2.0`, `license_link: https://ai.google.dev/gemma/docs/gemma_4_license`, `base_model: google/gemma-4-E2B-it-qat-q4_0-unquantized`. The text is the Gemma 4 model card for the quantisation-aware-training (QAT) releases and lists "GGUF (Q4_0)" among four official QAT formats. It states the licence as Apache 2.0 and adds no other notice, attribution requirement or use restriction. |
| Provenance conclusion | The GGUF is distributed by Google (publisher shown on Kaggle) as a Google-listed format of the E2B QAT checkpoint, under a variation licence field of Apache 2.0. This supports describing the file as an official Google release under Apache 2.0 **as stated by the publisher**. The file itself embeds no licence, and neither the card nor the file names the conversion tool or commit; that detail remains unknown and is not needed for the licence statement. |
| Prohibited Use Policy | Google's page (https://ai.google.dev/gemma/prohibited_use_policy, last modified 21 Feb 2024, marked deprecated) does not name Gemma 4 or Apache 2.0. Whether it applies to Gemma 4 is not stated anywhere found. The experiment uses the model only to rerank code-node identifiers locally, which is not a use the policy lists, but this record makes no claim about the policy's applicability. |
| Limitations of this record | Not legal advice; based on publisher statements read on the dates above, which may change. Redistribution of the weights is not undertaken, so the question of conversion-artefact terms does not arise for this release. |
| Handling here | Weights are not redistributed. `manifests/gemma4_manifest.json` records the Kaggle source, file and hash only. Users should obtain the file from Kaggle and read the licence on the variation page. |

## Analysed repositories (snapshots not included)
Licence files read from the downloaded snapshots at the pinned commits: Apache-2.0 (prefect, aiohttp, moto), BSD-3-Clause (dask, numpy, scipy, sympy; Django is BSD-3-Clause per its licence note), MIT (mypy, sqlglot), the Unlicense (yt-dlp). matplotlib uses its own licence text (not summarised here). Only short identifiers such as `module:function` names derived from these projects appear in aggregate outputs.

## Python dependencies (versions as resolved from `uv.lock` in the clean install; licences read from installed metadata; pandas, pyarrow, PyYAML, pytest, ruff, llama-cpp-python licences from the earlier local environment at the same versions)
networkx 3.7 (BSD-3-Clause), PyYAML 6.0.3 (MIT), pandas 3.0.6 (BSD-3-Clause), pyarrow 26.0.0 (Apache-2.0), SciPy 1.18.1 (BSD), llama-cpp-python 0.3.36 (MIT), pytest 9.1.1 (MIT), ruff 0.17.1 (MIT).

## References
Cited works are listed in `paper/references.bib`; verification depth per entry is in `submission/RELATED_WORK_AUDIT.md`.
