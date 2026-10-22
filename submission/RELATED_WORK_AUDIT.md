# Related-work audit (Checkpoint 2)

Access date: 2026-10-22. Method: arXiv/ACL abstract pages fetched directly; full-text PDFs for LocAgent, AgentNoiseBench and Agent Retrieval Bench extracted locally with `pdftotext` and searched. Search-engine snippets are marked as such and are not treated as verified. The manuscript has not been changed.

## A. Existing references: re-verification

| # | Work | Authors / year | Status | Identifier | Verified | Overlap with GraphFaultBench |
|---|---|---|---|---|---|---|
| 1 | LocAgent: Graph-Guided LLM Agents for Code Localization | Chen, Tang, Deng, Wu, Wu, Jiang, Prasanna, Cohan, Wang, 2025 | **Peer-reviewed**: ACL 2025 (Long Papers), pp. 8697–8727, DOI 10.18653/v1/2025.acl-long.426; arXiv v1 12 Mar 2025 | arXiv:2503.09089 | Abstract page and full text read | Builds directed heterogeneous graphs (files, classes, functions; imports, invocations, inheritance); introduces Loc-Bench (560 rows: 242 bug, 150 feature, 29 security, 139 performance). A text search of the full paper found no experiment degrading the graph. The word "robustness" appears only in generic senses. |
| 2 | Agent Retrieval Bench | Qin, Xie, 2026 | arXiv preprint, v1 27 Jul 2026, CC BY 4.0 | arXiv:2607.24882 | Abstract and full text read | Fifth subset: 50 natural no-gold cases plus 32 counterfactual wrong-repository controls. Thresholds calibrated with counterfactual controls do not improve selective success on the natural cases (the "calibration gap"). Natural-only recalibration also leaves no ranker improved. No graph corruption. |
| 3 | ARISE | Seddik, Seddik, Esmaeili, Sadatbenis, Fard, 2026 | arXiv preprint (v1 4 May 2026; v2 3 Jul 2026) | arXiv:2605.03117 | Abstract page only | Statement-level data-flow graph and toolset; SWE-bench Lite, Qwen2.5-Coder-32B; 22.0% resolved (66/300), +4.7 points over SWE-agent; Function Recall@1 0.43→0.60. No graph-degradation study seen at abstract level; full text not read (**U**). |
| 4 | AgentNoiseBench | Wang et al., 2026 | arXiv preprint (v1 11 Feb 2026) | arXiv:2602.11348 | Abstract and full text read | User-noise and tool-noise injected into existing agent benchmarks; average accuracy drop 20.8%; domains named are VitaBench, τ²-bench and Search (24.1%, 21.2%, 16.8%). No code-localisation domain seen. The manuscript's "of which graph corruption is a narrow instance" is an interpretation, not a claim made by the paper. |
| 5 | RepoAtlas | Zhang et al., 2026 | arXiv preprint (v1 15 Sep 2026) | arXiv:2609.16936 | Abstract page only | Training-free evolving multimodal repository views; SWE-bench Verified, +2.4 points over strongest multimodal graph baseline; −5.8% input tokens, −7.8% model calls. No degradation study at abstract level; full text not read (**U**). |

### Required corrections to existing references
1. Reference 1 should cite the ACL 2025 version (venue, pages, DOI) alongside or instead of arXiv. One automated page extraction rendered the second author as "Robert Tang"; the arXiv page gives "Xiangru Tang". The ACL page should be checked directly before the bibliography is finalised (**U**).
2. The manuscript says LocAgent "holds graph quality fixed". The abstract page and text search do not contradict this, but it should be phrased as "does not, to my reading, vary graph quality".
3. References 2–5 are preprints, not peer-reviewed; label them as such.
4. The manuscript's sentence that ARB's finding "resembles" the gate's non-transfer is acceptable if kept as an analogy: ARB's gap concerns synthetic versus natural no-gold cases, whereas the gate's non-transfer concerns the first corruption class used.

## B. Additional directly relevant work found

| Work | Status / identifier | What it does | Relation to GraphFaultBench |
|---|---|---|---|
| RepoGraph (Ouyang, Yu, Ma, Xiao, Zhang, Jia, Han, Zhang, Yu) | ICLR 2025; arXiv:2410.14684 (v1 3 Oct 2024) | Repository-level code graph plug-in; ego-graph retrieval; SWE-bench, CrossCodeEval | Same family as the graph-aided methods; no corruption study seen (abstract only). Should be cited. |
| SpIDER (Chaudhari, Jacob, Cao, Rashid, Goswami, Bock) | arXiv:2512.16956; marked EMNLP 2026 camera-ready | Dense retrieval plus graph exploration; SpIDER-Bench; gains grow once call edges are explored | Evidence that edge types matter for localisation, which motivates edge-removal stressors. Abstract only. Should be cited. |
| CoSIL (arXiv:2503.22424) | arXiv; search-snippet-level only (**U**) | LLM-built call-graph search for issue localisation; ablation removing the module call graph lowers function Top-1 from 0.430 to 0.383 (as reported by a search summary, not verified here) | Closest to a graph-ablation result, but it removes a graph layer rather than perturbing edges at controlled severity. Verify before citing. |
| OrcaLoca (ICML 2025; arXiv:2502.00350) | search-snippet-level only (**U**) | Agent framework for issue localisation | Context only. |
| Toward Robust GraphRAG (Ma et al., arXiv:2603.14828) | arXiv preprint, v1 16 Mar 2026 | Knowledge-graph QA under spurious-noise and incompleteness; CS-RAG falls back to text when graph support is weak; stable under injected KG errors | Conceptually the nearest to a graph-quality-aware fallback, but for knowledge graphs, not code. Abstract page read. Cite as an analogy and treat the "fallback" overlap honestly: the idea of graph-to-text fallback is not new. |

Searches run (extended and standard): robustness of code-graph retrieval to incomplete or noisy graphs; RepoGraph/CodeRAG; issue-localisation graph edge perturbation. No paper was found that systematically deletes, rewires or dangles edges of a code dependency graph at controlled severity and measures issue-localisation retrieval. This is absence of evidence from a bounded search, not proof; the search was not exhaustive (no Google Scholar/Semantic Scholar sweep, no full-text read of ARISE, RepoAtlas, RepoGraph, SpIDER, CoSIL).

## C. Novelty statement (narrow form to carry into Checkpoint 3)
Acceptable: "To my knowledge, and after a bounded search, I did not find a prior study that applies controlled, seeded corruption operators to a code dependency graph and measures the effect on issue-to-code retrieval. Graph-to-text fallback under unreliable graph evidence has been proposed for knowledge-graph QA (Ma et al.) and abstention under calibration gaps has been studied for repository retrieval (Qin and Xie), so the gate is not offered as a new idea."

Not acceptable: "first", "no prior work", "novel gate", or any claim that graph corruption in agents is unstudied.

## D. Full-text second pass (2026-10-22)

Sources actually read: the arXiv PDFs of ARISE (v2), RepoAtlas (v1), RepoGraph (v2, ICLR 2025 camera-ready format), SpIDER (v3) and CoSIL (v2), extracted with `pdftotext` and read by keyword search of the whole text plus reading of the relevant passages. This was not a line-by-line read of every section; appendices were searched, not read. Identity checked against title, authors and arXiv identifier on the PDF's first page.

| Work | Identity check | What it does | Any graph-quality or corruption experiment? | Overlap with GraphFaultBench |
|---|---|---|---|---|
| ARISE | Title, authors (FARD Lab, UBC) and arXiv:2605.03117v2 (3 Jul 2026) match | Multi-granularity graph with Contains, Imports, Inherits and resolved Calls edges plus statement-level def-use edges; three-tier tool API | No controlled degradation. A design remark states that spurious call edges are "more harmful than missing edges", citing other work ([33] is Shi et al., ICML 2023, on LLM distraction by irrelevant context). It then resolves only unambiguous calls. The ablations concern the data-flow graph and tool schema. | Supports the motivation for `stale_rewire` (wrong edges) versus deletion, but as an unmeasured design assumption. My results do not test that claim for LLM agents. |
| RepoAtlas | Title, authors (Beihang University) and arXiv:2609.16936 match | Budgeted, evolving views from a code graph; ablations include removing PageRank propagation and the node budget; selection stage evaluated on LocBench | No corruption of the input graph. Ablations remove pipeline components. | Uses graph-based relevance propagation (PageRank) that my `repomap` baseline resembles; independent of corruption. |
| RepoGraph | Title, authors and ICLR 2025 header match; arXiv:2410.14684 | Line-level graph with `invoke` and `contain` edges; ego-graph retrieval; adds file/function/line localisation gains to RAG, Agentless and AutoCodeRover | None found by keyword search | Same graph-aided family; no degradation study. |
| SpIDER | Title, authors and arXiv:2512.16956v3 match; EMNLP 2026 camera-ready per the arXiv page | Dense retrieval plus graph exploration over containment and call edges; "robustness" in the paper means cross-language generalisation (RQ2), not graph corruption | None | Reports gains from adding call edges, so edge information is informative; does not test missing or wrong edges. |
| CoSIL | PDF title is now "Issue Localization via LLM-Driven Iterative Code Graph Searching" (Jiang, Ren, Yan, Jiang, Li, Liu); v1 title was "CoSIL: Software Issue Localization via LLM-Driven Code Repository Graph Searching"; arXiv:2503.22424. Use the current title and note the identifier. | Module call graph then function call graph, iterative LLM search, pruning | Component ablation only: removing the module call graph reduces file-level and function-level scores (e.g. function Top-1 0.430→0.383, a 11.5% relative drop, in the paper's table); this removes a whole layer, not edges at controlled severity | The closest existing evidence that call-graph information matters. It is an ablation, not a severity sweep, and does not corrupt edges. |

### Corrections to Section A and B
- ARISE and RepoAtlas are now read beyond the abstract; neither contains an input-graph degradation experiment that I found.
- The ARISE sentence about spurious edges is a relevant prior claim and should be cited as motivation, labelled as an assertion in that paper.
- OrcaLoca (ICML 2025; arXiv:2502.00350) remains snippet-level and is excluded from the manuscript unless read.

### Limits of the search
- Bounded: three web searches plus citation-following from the papers above; no Google Scholar, Semantic Scholar or ACL/ICSE/FSE proceedings sweep; English only; post-June-2026 work may be missed.
- Keyword search of full texts can miss experiments described in other words.
- The search cannot establish absence of prior work.

## E. Open items
- LocAgent author discrepancy: **resolved for citation purposes (2026-10-22).** The official ACL Anthology BibTeX (`aclanthology.org/2025.acl-long.426.bib`) lists the authors as Zhaoling Chen, Robert Tang, Gangda Deng, Fang Wu, Jialong Wu, Zhiwei Jiang, Viktor Prasanna, Arman Cohan, Xingyao Wang; pages 8697–8727, DOI 10.18653/v1/2025.acl-long.426. The arXiv listing (2503.09089) gives the second author as Xiangru Tang. The manuscript follows the ACL metadata for the proceedings citation (initials "R. Tang") and does not assert which given name is correct; the arXiv difference is recorded here only.
- OrcaLoca not read.
