#!/usr/bin/env python3
"""Record the Milestone-10 measured before/after into eval/history.jsonl (spec 0079).

A **dev-time, run-once** checkpoint (like ``scripts/record_m9_close.py``), not part of
the runtime. It appends two deliberate journal points — the same-name / **same-address**
disambiguation pair (two distinct "Havel Kontor GmbH" firms at one address) turns the
ambiguous-name gold question from a wrongly-*answered* miss into a correct *refusal*
when the registration key is added:

- **before** — Milestone-9 ER (name + address, ``match_fields=ADDRESS_MATCH_FIELDS``):
  the address *agrees* (it is the same), so it corroborates a merge and the two firms
  over-merge — the ambiguous-name gold question is wrongly ANSWERED. Business gold
  quality **0.909** (10 / 11). Faithfulness 1.0 (the answer is faithful to its merged
  cluster). This is the floor name + address ER cannot reach.
- **after** — Milestone-10 ER (the registration key leads ``match_fields``, the
  registry default): the two firms carry different VATs, so the key splits them and the
  question correctly REFUSES — business gold quality **1.000**, CI-reproducible (unlike
  the M6/M7 online closes). Faithfulness 1.0.

Both stamped ``2026-06-28`` (the milestone date) via the ``recorded`` override, so the
journal is deterministic rather than wall-clock. Run once:

    uv run python scripts/record_m10_close.py
"""

from __future__ import annotations

import dataclasses

from tessera.business.knowledge import build_demo_graph
from tessera.eval.harness import run_eval
from tessera.eval.history import record
from tessera.eval.registry import (
    business_battery,
    devex_battery,
    github_actions_battery,
)
from tessera.sources.salt import ADDRESS_MATCH_FIELDS

RECORDED = "2026-06-28"

_BEFORE_NOTE = (
    "M10 before: Milestone-9 ER (name + address) over the new same-name/SAME-address "
    "disambiguation pair (two distinct 'Havel Kontor GmbH' firms at one address). The "
    "address AGREES, so it corroborates a merge and the firms over-merge — the "
    "ambiguous-name gold question is wrongly ANSWERED. Business gold quality 0.909. "
    "Faithfulness 1.0 (the answer is faithful to its merged cluster). The floor name + "
    "address ER cannot reach."
)
_AFTER_NOTE = (
    "M10 after: registration-key ER (VATRegistration leads match_fields) splits the "
    "two same-named/same-addressed firms on their different VATs, so the "
    "ambiguous-name gold question correctly REFUSES — business gold quality 1.000, "
    "CI-reproducible. Faithfulness 1.0. The new floor is same name + address + key."
)


def main() -> None:
    address_only_business = dataclasses.replace(
        business_battery(),
        build_graph=lambda: build_demo_graph(match_fields=ADDRESS_MATCH_FIELDS),
    )
    before = run_eval(
        [address_only_business, devex_battery(), github_actions_battery()]
    )
    record(before, note=_BEFORE_NOTE, recorded=RECORDED)

    after = run_eval()  # the registry default: registration-key business ER
    record(after, note=_AFTER_NOTE, recorded=RECORDED)
    print("Recorded M10 before/after to eval/history.jsonl; badge refreshed.")


if __name__ == "__main__":
    main()
