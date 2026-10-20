"""Unit tests for the small amount of new, non-reused logic added in
`experiments/pilot_a/run_coverage_floor_eval.py` (Phase 4): the
threshold-unchanged guard and the per-row metric scoring helper. The
script's core pipeline (graph building, corruption, ranking, metrics,
bootstrap CI) all call existing, already-tested functions from
`gemma_research.evidence.retrieve`, `gemma_research.evidence.perturb`,
`gemma_research.evidence.gold_visibility` and
`gemma_research.metrics.scoring` directly and is exercised end-to-end by
the real run recorded in `results/coverage_floor_eval/`, so this file only
covers the script's own helper functions, loaded by path since
`experiments/` is not an installed package.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from gemma_research.data.types import RankedCandidate
from gemma_research.evidence.retrieve import DiagnosticGate

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "experiments" / "pilot_a" / "run_coverage_floor_eval.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("run_coverage_floor_eval", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def test_assert_gate_thresholds_unchanged_passes_against_real_defaults():
    gate = mod._assert_gate_thresholds_unchanged()
    assert isinstance(gate, DiagnosticGate)
    assert gate.coverage_floor == 0.6
    assert gate.isolated_ceiling == 0.5
    assert gate.anchor_floor == 0.1


def test_assert_gate_thresholds_unchanged_fails_loudly_if_defaults_drift(monkeypatch):
    class DriftedGate(DiagnosticGate):
        def __init__(self, coverage_floor: float = 0.9, isolated_ceiling: float = 0.5, anchor_floor: float = 0.1):
            super().__init__(coverage_floor, isolated_ceiling, anchor_floor)

    monkeypatch.setattr(mod, "DiagnosticGate", DriftedGate)
    with pytest.raises(AssertionError):
        mod._assert_gate_thresholds_unchanged()


def test_score_row_hit_and_mrr_on_gold_in_top_rank():
    ranking = (
        RankedCandidate(node_id="gold", score=1.0),
        RankedCandidate(node_id="other", score=0.5),
    )
    gold = frozenset({"gold"})
    scores = mod._score_row(ranking, gold)
    assert scores["hit_at_1"] == 1.0
    assert scores["hit_at_3"] == 1.0
    assert scores["hit_at_5"] == 1.0
    assert scores["strict_acc_at_5"] == 1.0
    assert scores["mrr"] == 1.0


def test_score_row_miss_when_gold_absent_from_ranking():
    ranking = (
        RankedCandidate(node_id="other1", score=1.0),
        RankedCandidate(node_id="other2", score=0.5),
    )
    gold = frozenset({"gold"})
    scores = mod._score_row(ranking, gold)
    assert scores["hit_at_1"] == 0.0
    assert scores["hit_at_5"] == 0.0
    assert scores["strict_acc_at_5"] == 0.0
    assert scores["mrr"] == 0.0


def test_score_row_strict_acc_requires_all_gold_ids_in_top_k():
    ranking = (
        RankedCandidate(node_id="gold1", score=1.0),
        RankedCandidate(node_id="other", score=0.9),
        RankedCandidate(node_id="gold2", score=0.1),
    )
    gold = frozenset({"gold1", "gold2"})
    scores = mod._score_row(ranking, gold)
    assert scores["hit_at_1"] == 1.0  # gold1 is top-1
    assert scores["strict_acc_at_5"] == 1.0  # both gold ids are within top 5
    # Only within top 2, gold2 is missing (rank 3), so strict top-2 would fail;
    # strict_acc_at_k here is evaluated at k=5 by _score_row, consistent with
    # the pre-registered k_values used throughout this project.
