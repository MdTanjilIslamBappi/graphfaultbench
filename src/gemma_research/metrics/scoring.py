"""Localization metrics shared across all baselines and candidates.

Kept deliberately small: Hit@k, MRR, and a paired bootstrap CI over
per-task scores. Pre-registration note (contingency doc protocol step 6):
whichever single metric is pre-registered as primary for a given
experiment must be recorded in that experiment's config, not decided
after seeing results.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from gemma_research.data.types import RankedCandidate


def hit_at_k(ranking: tuple[RankedCandidate, ...], gold_ids: frozenset[str], k: int) -> float:
    top_k = {c.node_id for c in ranking[:k]}
    return 1.0 if top_k & gold_ids else 0.0


def recall_at_k(ranking: tuple[RankedCandidate, ...], gold_ids: frozenset[str], k: int) -> float:
    if not gold_ids:
        raise ValueError("recall_at_k undefined for a task with no gold ids")
    top_k = {c.node_id for c in ranking[:k]}
    return len(top_k & gold_ids) / len(gold_ids)


def reciprocal_rank(ranking: tuple[RankedCandidate, ...], gold_ids: frozenset[str]) -> float:
    for rank, cand in enumerate(ranking, start=1):
        if cand.node_id in gold_ids:
            return 1.0 / rank
    return 0.0


def strict_acc_at_k(ranking: tuple[RankedCandidate, ...], gold_ids: frozenset[str], k: int) -> float:
    """1.0 only if ALL gold ids are in the top k (vs. hit_at_k's "any gold id").

    Distinguishes "found *a* relevant file" from "found *every* file that
    needed editing" (directive §3, last bullet).
    """
    if not gold_ids:
        raise ValueError("strict_acc_at_k undefined for a task with no gold ids")
    top_k = {c.node_id for c in ranking[:k]}
    return 1.0 if gold_ids.issubset(top_k) else 0.0


@dataclass(frozen=True)
class BootstrapCI:
    point_estimate: float
    low: float
    high: float
    n_resamples: int


def bootstrap_ci(
    per_task_scores: list[float], n_resamples: int = 2000, alpha: float = 0.05, seed: int = 0
) -> BootstrapCI:
    """Simple (non-clustered) bootstrap over per-task scores. Callers wanting
    repository-clustered resampling (contingency doc protocol step 6, for
    datasets with few repositories) should resample whole repositories
    upstream and pass already-grouped scores in."""
    if not per_task_scores:
        raise ValueError("per_task_scores must be non-empty")
    rng = random.Random(seed)
    n = len(per_task_scores)
    point = statistics.fmean(per_task_scores)
    resample_means = []
    for _ in range(n_resamples):
        sample = [per_task_scores[rng.randrange(n)] for _ in range(n)]
        resample_means.append(statistics.fmean(sample))
    resample_means.sort()
    lo_idx = int((alpha / 2) * n_resamples)
    hi_idx = int((1 - alpha / 2) * n_resamples) - 1
    return BootstrapCI(
        point_estimate=point,
        low=resample_means[max(0, lo_idx)],
        high=resample_means[min(n_resamples - 1, hi_idx)],
        n_resamples=n_resamples,
    )


def bootstrap_ci_clustered(
    cluster_scores: dict[str, list[float]], n_resamples: int = 2000, alpha: float = 0.05, seed: int = 0
) -> BootstrapCI:
    """Bootstrap resampling whole clusters (repositories), not individual
    tasks — required when tasks within a repository are not independent
    (shared codebase/style), per the directive's "resampling unit...
    grouping by repository" requirement. With few clusters this interval is
    necessarily wide; that width is itself informative, not a bug to average
    away by resampling at the task level instead.
    """
    clusters = [c for c in cluster_scores.values() if c]
    if not clusters:
        raise ValueError("cluster_scores must contain at least one non-empty cluster")
    rng = random.Random(seed)
    n_clusters = len(clusters)
    all_scores = [s for c in clusters for s in c]
    point = statistics.fmean(all_scores)

    resample_means = []
    for _ in range(n_resamples):
        sampled_clusters = [clusters[rng.randrange(n_clusters)] for _ in range(n_clusters)]
        pooled = [s for c in sampled_clusters for s in c]
        resample_means.append(statistics.fmean(pooled))
    resample_means.sort()
    lo_idx = int((alpha / 2) * n_resamples)
    hi_idx = int((1 - alpha / 2) * n_resamples) - 1
    return BootstrapCI(
        point_estimate=point,
        low=resample_means[max(0, lo_idx)],
        high=resample_means[min(n_resamples - 1, hi_idx)],
        n_resamples=n_resamples,
    )
