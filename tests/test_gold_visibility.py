from gemma_research.evidence.gold_visibility import (
    any_gold_hidden,
    gold_hidden_fraction,
    gold_hidden_ids,
)


def test_gold_hidden_ids_returns_empty_when_no_overlap():
    gold = frozenset({"a", "b"})
    hidden = frozenset({"c", "d"})
    assert gold_hidden_ids(gold, hidden) == frozenset()


def test_gold_hidden_ids_returns_intersection_on_partial_overlap():
    gold = frozenset({"a", "b", "c"})
    hidden = frozenset({"b", "c", "z"})
    assert gold_hidden_ids(gold, hidden) == frozenset({"b", "c"})


def test_any_gold_hidden_false_when_no_overlap():
    gold = frozenset({"a", "b"})
    hidden = frozenset({"c"})
    assert any_gold_hidden(gold, hidden) is False


def test_any_gold_hidden_true_on_single_overlapping_id():
    gold = frozenset({"a", "b"})
    hidden = frozenset({"b", "x", "y"})
    assert any_gold_hidden(gold, hidden) is True


def test_any_gold_hidden_false_when_hidden_set_is_empty():
    gold = frozenset({"a"})
    hidden: frozenset[str] = frozenset()
    assert any_gold_hidden(gold, hidden) is False


def test_gold_hidden_fraction_is_zero_for_empty_gold_set():
    gold: frozenset[str] = frozenset()
    hidden = frozenset({"a", "b"})
    assert gold_hidden_fraction(gold, hidden) == 0.0


def test_gold_hidden_fraction_is_one_when_all_gold_hidden():
    gold = frozenset({"a", "b"})
    hidden = frozenset({"a", "b", "c"})
    assert gold_hidden_fraction(gold, hidden) == 1.0


def test_gold_hidden_fraction_is_partial_for_multi_gold_task():
    gold = frozenset({"a", "b", "c", "d"})
    hidden = frozenset({"a", "c"})
    assert gold_hidden_fraction(gold, hidden) == 0.5


def test_gold_hidden_fraction_zero_when_no_overlap():
    gold = frozenset({"a", "b"})
    hidden = frozenset({"z"})
    assert gold_hidden_fraction(gold, hidden) == 0.0
