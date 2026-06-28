"""The Milestone-9 measured close: multi-field ER turns an over-merge miss into a
correct refusal (spec 0075).

The synthetic SALT corpus carries two genuinely distinct firms with the IDENTICAL
name "Hanseatic Trading GmbH" at different addresses (Hamburg / Munich). Name-only ER
over-merges them into one entity, so the ambiguous-name gold question resolves to a
single wrong entity and *answers* it — a measured **quality** miss. Multi-field ER
(name + address) splits them, so the question correctly *refuses* as ambiguous — the
close. Faithfulness stays 1.0 in both arms (the name-only answer is faithful to its
merged cluster; the gate measures structure, not the right entity).

This is the headline before/after, **CI-reproducible** (unlike the M6/M7 online
closes), and recorded in ``eval/history.jsonl`` (``scripts/record_m9_close.py``).
"""

from __future__ import annotations

import dataclasses

import pytest

from tessera.business.composition import compose
from tessera.business.knowledge import build_demo_graph
from tessera.eval.harness import BatteryResult, run_eval
from tessera.eval.registry import business_battery


def _business_gold(*, match_fields: tuple[str, ...]) -> BatteryResult:
    battery = dataclasses.replace(
        business_battery(),
        build_graph=lambda: build_demo_graph(match_fields=match_fields),
    )
    return run_eval([battery]).batteries[0]


def test_name_only_er_misses_the_ambiguous_name_question() -> None:
    """Before: name-only ER over-merges the same-named firms, so compose answers the
    ambiguous-name question instead of refusing — gold quality 0.900, faithfulness
    still 1.0 (the wrong answer is faithful to its merged cluster)."""
    result = _business_gold(match_fields=())
    assert result.quality == pytest.approx(0.9)
    assert result.faithfulness == pytest.approx(1.0)


def test_multifield_er_closes_the_ambiguous_name_question() -> None:
    """After: multi-field ER splits the firms, so compose refuses the ambiguous-name
    question — gold quality back to 1.000, faithfulness and coverage 1.0,
    CI-reproducible."""
    result = _business_gold(match_fields=("postal_code", "city_name"))
    assert result.quality == pytest.approx(1.0)
    assert result.faithfulness == pytest.approx(1.0)
    assert result.coverage == pytest.approx(1.0)


def test_the_gold_question_flips_from_answer_to_refusal() -> None:
    """The mechanism behind the number: the same compose call is grounded under
    name-only ER (it answers the merged entity) and a refusal under multi-field ER
    (the two same-named entities tie → ambiguous)."""
    question = "Summarise Hanseatic Trading GmbH."
    assert compose(question, build_demo_graph(match_fields=())).is_grounded  # miss
    assert not compose(question, build_demo_graph()).is_grounded  # close (refusal)
