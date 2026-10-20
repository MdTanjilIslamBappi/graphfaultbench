import pytest

from gemma_research.data.types import RankedCandidate
from gemma_research.metrics.scoring import (
    bootstrap_ci,
    bootstrap_ci_clustered,
    hit_at_k,
    recall_at_k,
    reciprocal_rank,
    strict_acc_at_k,
)


def _ranking(*ids: str) -> tuple[RankedCandidate, ...]:
    return tuple(RankedCandidate(node_id=nid, score=1.0 - i * 0.01) for i, nid in enumerate(ids))


def test_hit_at_k_true_and_false():
    ranking = _ranking("a", "b", "c")
    assert hit_at_k(ranking, frozenset({"b"}), k=2) == 1.0
    assert hit_at_k(ranking, frozenset({"c"}), k=2) == 0.0


def test_recall_at_k_partial_credit():
    ranking = _ranking("a", "b", "c", "d")
    assert recall_at_k(ranking, frozenset({"a", "c", "z"}), k=3) == pytest.approx(2 / 3)


def test_recall_at_k_rejects_empty_gold():
    ranking = _ranking("a", "b")
    with pytest.raises(ValueError):
        recall_at_k(ranking, frozenset(), k=1)


def test_reciprocal_rank():
    ranking = _ranking("a", "b", "c")
    assert reciprocal_rank(ranking, frozenset({"b"})) == pytest.approx(0.5)
    assert reciprocal_rank(ranking, frozenset({"zzz"})) == 0.0


def test_bootstrap_ci_is_deterministic_and_contains_point_estimate():
    scores = [1.0, 0.0, 1.0, 1.0, 0.0]
    ci1 = bootstrap_ci(scores, n_resamples=500, seed=0)
    ci2 = bootstrap_ci(scores, n_resamples=500, seed=0)
    assert ci1 == ci2
    assert ci1.low <= ci1.point_estimate <= ci1.high


def test_bootstrap_ci_rejects_empty_input():
    with pytest.raises(ValueError):
        bootstrap_ci([])


def test_strict_acc_at_k_requires_all_gold():
    ranking = _ranking("a", "b", "c", "d")
    assert strict_acc_at_k(ranking, frozenset({"a", "b"}), k=3) == 1.0
    assert strict_acc_at_k(ranking, frozenset({"a", "d"}), k=3) == 0.0  # "d" outside top-3


def test_strict_acc_at_k_rejects_empty_gold():
    ranking = _ranking("a", "b")
    with pytest.raises(ValueError):
        strict_acc_at_k(ranking, frozenset(), k=1)


def test_bootstrap_ci_clustered_deterministic_and_contains_point_estimate():
    clusters = {"repoA": [1.0, 1.0, 0.0], "repoB": [0.0, 0.0], "repoC": [1.0]}
    ci1 = bootstrap_ci_clustered(clusters, n_resamples=500, seed=0)
    ci2 = bootstrap_ci_clustered(clusters, n_resamples=500, seed=0)
    assert ci1 == ci2
    assert ci1.low <= ci1.point_estimate <= ci1.high


def test_bootstrap_ci_clustered_rejects_empty_input():
    with pytest.raises(ValueError):
        bootstrap_ci_clustered({})
