#!/usr/bin/env python3
"""Record the Milestone-9 measured before/after into eval/history.jsonl (spec 0075).

A **dev-time, run-once** checkpoint (like ``scripts/generate_salt_synthetic.py``),
not part of the runtime. It appends two deliberate journal points — the same-name /
different-address disambiguation pair turns the ambiguous-name gold question from a
wrongly-*answered* miss (name-only ER) into a correct *refusal* (multi-field ER):

- **before** — name-only ER (``match_fields=()``): business gold quality **0.900**.
  This is a counterfactual baseline — the Milestone-9 data did not exist at
  Milestone 8 — so the note says so. It measures the *prior engine's* limitation over
  the new harder data, faithfulness still 1.0.
- **after** — multi-field ER (the registry default): business gold quality **1.000**,
  CI-reproducible (unlike the M6/M7 online closes).

Both stamped ``2026-06-28`` (the milestone date) via the ``recorded`` override, so the
journal is deterministic rather than wall-clock. Run once:

    uv run python scripts/record_m9_close.py
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

RECORDED = "2026-06-28"

_BEFORE_NOTE = (
    "M9 before (counterfactual baseline; this exact state did not ship at M8): "
    "name-only ER over the new same-name/different-address disambiguation pair "
    "over-merges the two distinct 'Hanseatic Trading GmbH' firms, so the "
    "ambiguous-name gold question is wrongly ANSWERED — business gold quality 0.900. "
    "Faithfulness 1.0 (the answer is faithful to its merged cluster)."
)
_AFTER_NOTE = (
    "M9 after: multi-field ER (name + address) splits the two same-named firms on "
    "their different postal codes, so the ambiguous-name gold question correctly "
    "REFUSES — business gold quality 1.000, CI-reproducible. Faithfulness 1.0."
)


def main() -> None:
    name_only_business = dataclasses.replace(
        business_battery(),
        build_graph=lambda: build_demo_graph(match_fields=()),
    )
    before = run_eval([name_only_business, devex_battery(), github_actions_battery()])
    record(before, note=_BEFORE_NOTE, recorded=RECORDED)

    after = run_eval()  # the registry default: multi-field business
    record(after, note=_AFTER_NOTE, recorded=RECORDED)
    print("Recorded M9 before/after to eval/history.jsonl; badge refreshed.")


if __name__ == "__main__":
    main()
