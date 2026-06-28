"""The Milestone-10 measured close: the registration key turns an over-merge miss
that name + address ER cannot reach into a correct refusal (spec 0079).

The synthetic SALT corpus carries two genuinely distinct firms with the IDENTICAL name
"Havel Kontor GmbH" at the IDENTICAL address (Am Kanal 5, 14467 Potsdam). Milestone-9 ER
(name + address) cannot tell them apart — the address *agrees*, so it corroborates a
merge and the two firms over-merge into one entity; the ambiguous-name gold question
resolves to a single wrong entity and *answers* it (a measured **quality** miss).
Milestone-10 ER adds the registration key (the two firms carry different VATs), which
splits them, so the question correctly *refuses* as ambiguous — the close. Faithfulness
stays 1.0 in both arms (the address-only answer is faithful to its merged cluster; the
gate measures structure, not the right entity).

This is the headline before/after, **CI-reproducible** (unlike the M6/M7 online closes),
and recorded in ``eval/history.jsonl`` (``scripts/record_m10_close.py``). It is the
registration-key analogue of the Milestone-9 close (``test_m9_multifield_close``), one
floor deeper: M9 split a same-name/*different*-address pair on the address; M10 splits a
same-name/*same*-address pair on the key.
"""

from __future__ import annotations

import dataclasses

import pytest

from tessera.business.composition import compose
from tessera.business.knowledge import build_demo_graph
from tessera.eval.harness import BatteryResult, run_eval
from tessera.eval.registry import business_battery
from tessera.sources.salt import ADDRESS_MATCH_FIELDS


def _business_gold(*, match_fields: tuple[str, ...] | None) -> BatteryResult:
    build = (
        build_demo_graph
        if match_fields is None
        else (lambda: build_demo_graph(match_fields=match_fields))
    )
    battery = dataclasses.replace(business_battery(), build_graph=build)
    return run_eval([battery]).batteries[0]


def test_address_only_er_misses_the_same_address_question() -> None:
    """Before: name + address ER (Milestone 9) over-merges the same-named/same-addressed
    firms — the address agrees — so compose answers the ambiguous-name question instead
    of refusing. Gold quality 0.909 (10 / 11), faithfulness still 1.0 (the wrong answer
    is faithful to its merged cluster)."""
    result = _business_gold(match_fields=ADDRESS_MATCH_FIELDS)
    assert result.quality == pytest.approx(10 / 11)
    assert result.faithfulness == pytest.approx(1.0)


def test_registration_key_closes_the_same_address_question() -> None:
    """After: the registration key (the registry default) splits the firms on their
    different VATs, so compose refuses the ambiguous-name question — gold quality back
    to 1.000, faithfulness and coverage 1.0, CI-reproducible."""
    result = _business_gold(match_fields=None)  # the registration-key default
    assert result.quality == pytest.approx(1.0)
    assert result.faithfulness == pytest.approx(1.0)
    assert result.coverage == pytest.approx(1.0)


def test_the_gold_question_flips_from_answer_to_refusal() -> None:
    """The mechanism behind the number: the same compose call is grounded under name +
    address ER (it answers the merged entity) and a refusal under the registration key
    (the two same-named/same-addressed entities tie → ambiguous)."""
    question = "Summarise Havel Kontor GmbH."
    address_only = build_demo_graph(match_fields=ADDRESS_MATCH_FIELDS)
    assert compose(question, address_only).is_grounded  # miss (over-merged → answers)
    assert not compose(question, build_demo_graph()).is_grounded  # close (refusal)
