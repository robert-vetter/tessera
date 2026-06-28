"""The Milestone-9 measured close: multi-field (name + address) ER turns an over-merge
miss into a correct refusal (spec 0075).

The synthetic SALT corpus carries two genuinely distinct firms with the IDENTICAL name
"Hanseatic Trading GmbH" at *different* addresses (Hamburg / Munich). Name-only ER
over-merges them into one entity, so the ambiguous-name gold question resolves to a
single wrong entity and *answers* it — a measured **quality** miss. Multi-field ER (name
+ address) splits them on their different addresses, so the question correctly *refuses*
as ambiguous — the close. Faithfulness stays 1.0 in both arms (the name-only answer is
faithful to its merged cluster; the gate measures structure, not the right entity).

Milestone 10 (spec 0079) adds a SECOND same-name pair at the *same* address (Havel
Kontor GmbH), which the address gate cannot reach — so the absolute gold-quality numbers
below now reflect both pairs: the address gate closes the different-address pair only.
The same-address pair is closed by the registration key (see
``test_m10_registration_key_close``). This file is CI-reproducible (unlike M6/M7).
"""

from __future__ import annotations

import dataclasses

import pytest

from tessera.business.composition import compose
from tessera.business.knowledge import build_demo_graph
from tessera.eval.harness import BatteryResult, run_eval
from tessera.eval.registry import business_battery

_ADDRESS = ("postal_code", "city_name")


def _business_gold(*, match_fields: tuple[str, ...]) -> BatteryResult:
    battery = dataclasses.replace(
        business_battery(),
        build_graph=lambda: build_demo_graph(match_fields=match_fields),
    )
    return run_eval([battery]).batteries[0]


def test_name_only_er_misses_both_ambiguous_name_questions() -> None:
    """Before any field signal: name-only ER over-merges BOTH same-name disambiguation
    pairs (Hanseatic different-address, Havel same-address), so compose answers both
    ambiguous-name questions instead of refusing — gold quality 9/11, faithfulness still
    1.0 (each wrong answer is faithful to its merged cluster)."""
    result = _business_gold(match_fields=())
    assert result.quality == pytest.approx(9 / 11)
    assert result.faithfulness == pytest.approx(1.0)


def test_address_er_closes_only_the_different_address_pair() -> None:
    """Multi-field (name + address) ER splits the Hanseatic *different*-address pair, so
    its question refuses — but it cannot reach the Havel *same*-address pair (the
    address agrees), which still over-merges and answers. Gold quality 10/11: the
    address gate is a partial close, motivating the registration key (Milestone 10)."""
    result = _business_gold(match_fields=_ADDRESS)
    assert result.quality == pytest.approx(10 / 11)
    assert result.faithfulness == pytest.approx(1.0)


def test_the_hanseatic_question_flips_from_answer_to_refusal() -> None:
    """The mechanism behind the number: the Hanseatic ambiguous-name compose call is
    grounded under name-only ER (it answers the merged entity) and a refusal once the
    address splits the different-address firms (the two entities tie → ambiguous)."""
    question = "Summarise Hanseatic Trading GmbH."
    assert compose(question, build_demo_graph(match_fields=())).is_grounded  # miss
    assert not compose(
        question, build_demo_graph(match_fields=_ADDRESS)
    ).is_grounded  # close (refusal)
