"""Gemma 4 (E2B, local GGUF/CPU inference) as a reranker over a bounded
candidate pool — the optional downstream demonstration described in
`Gemma4_Research_Contingency_v2.md` ("For downstream agent validation, test
a small stratified sample with an accessible Gemma 4 model") and
`Gemma4_Paper_Track_Competition_Playbook.md` ("one small, properly
controlled Gemma 4 downstream demonstration... label that as secondary
evidence and report full generation parameters").

Design choice, stated explicitly for reproducibility: Gemma reranks the SAME
top-N candidate pool `fixed_hybrid_rank` already produces, rather than
choosing freely from the whole graph. This isolates one question — does an
LLM reranking layer improve top-5 selection quality within a fixed
candidate pool, compared to taking the pool's own top 5 — from a different
question (retrieval recall of the shortlist itself), which this small demo
does not attempt to answer. See `research/gemma4_downstream_go_no_go.md`.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from gemma_research.data.types import CodeGraph, RankedCandidate
from gemma_research.evidence.retrieve import BM25Index, fixed_hybrid_rank

GENERATION_PARAMS = {
    "temperature": 0.0,
    "top_p": 0.95,
    "top_k": 64,
    "max_tokens": 200,
}  # top_p/top_k are Gemma 4's own documented recommended sampling config;
# temperature is pinned to 0.0 here (not the documented 1.0) for
# reproducibility in this small, deterministic demonstration — reported
# explicitly as a deviation, not silently.

_CANDIDATE_TEXT_CHARS = 100
_QUERY_TEXT_CHARS = 700

_NODE_ID_LINE_RE = re.compile(r"[A-Za-z0-9_./:\-]+")


@dataclass(frozen=True)
class GemmaRerankResult:
    ranking: tuple[RankedCandidate, ...]
    raw_output: str
    candidate_pool: tuple[str, ...]
    n_parsed_valid: int
    runtime_seconds: float
    prompt_tokens: int
    completion_tokens: int


def _build_prompt(query_text: str, candidates: tuple[RankedCandidate, ...], graph: CodeGraph) -> str:
    nodes_by_id = {n.node_id: n for n in graph.nodes}
    lines = []
    for c in candidates:
        node = nodes_by_id.get(c.node_id)
        if node is None:
            continue
        snippet = node.text.replace("\n", " ").strip()[:_CANDIDATE_TEXT_CHARS]
        lines.append(f"- {node.node_id} ({node.kind}): {snippet}")
    candidate_block = "\n".join(lines)
    issue = query_text.replace("\n", " ").strip()[:_QUERY_TEXT_CHARS]
    return (
        "You are helping localize a software issue to the most relevant code symbols.\n\n"
        f"Issue report:\n{issue}\n\n"
        f"Candidate symbols (already shortlisted by a lexical+graph retriever):\n{candidate_block}\n\n"
        "List the 5 candidate symbol ids most likely to need editing to fix this issue, "
        "most likely first, one id per line, copied exactly as given above. "
        "Output only the ids, nothing else."
    )


def gemma_rerank(
    llm,
    graph: CodeGraph,
    query_text: str,
    pool_size: int = 15,
    bm25_index: BM25Index | None = None,
) -> GemmaRerankResult:
    """Rerank `fixed_hybrid_rank`'s top `pool_size` candidates using `llm`
    (a `llama_cpp.Llama` instance already loaded by the caller — loading the
    ~3.3 GB checkpoint once per process, not once per task, is a performance
    necessity here, not a methodological shortcut)."""
    full_ranking = fixed_hybrid_rank(graph, query_text, bm25_index=bm25_index)
    pool = full_ranking[:pool_size]
    pool_ids = tuple(c.node_id for c in pool)

    prompt = _build_prompt(query_text, pool, graph)
    t0 = time.perf_counter()
    out = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=GENERATION_PARAMS["max_tokens"],
        temperature=GENERATION_PARAMS["temperature"],
        top_p=GENERATION_PARAMS["top_p"],
        top_k=GENERATION_PARAMS["top_k"],
    )
    elapsed = time.perf_counter() - t0
    raw_output = out["choices"][0]["message"]["content"] or ""
    usage = out["usage"]

    pool_id_set = set(pool_ids)
    picked: list[str] = []
    for line in raw_output.splitlines():
        line = line.strip().lstrip("-*0123456789. \t")
        if line in pool_id_set and line not in picked:
            picked.append(line)
        if len(picked) == 5:
            break
    # Fallback: a pool id could appear mid-line (e.g. "1. src/foo.py:Bar — ...").
    if not picked:
        for line in raw_output.splitlines():
            for token in _NODE_ID_LINE_RE.findall(line):
                if token in pool_id_set and token not in picked:
                    picked.append(token)
            if len(picked) == 5:
                break

    remaining = [nid for nid in pool_ids if nid not in picked]
    n_picked = len(picked)
    ranked = [
        RankedCandidate(node_id=nid, score=float(n_picked - i)) for i, nid in enumerate(picked)
    ] + [RankedCandidate(node_id=nid, score=0.0) for nid in remaining]

    return GemmaRerankResult(
        ranking=tuple(ranked),
        raw_output=raw_output,
        candidate_pool=pool_ids,
        n_parsed_valid=n_picked,
        runtime_seconds=elapsed,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )
