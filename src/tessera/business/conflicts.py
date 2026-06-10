"""Conflicting-evidence detection: surface disagreement, never pick silently.

The project's #1 named failure mode (PROJECT_BRIEF §1) is *silent source
mixing* — two sources disagree and the system blends or picks one without
saying so. This module is the Phase 2 slice of the antidote, deliberately
narrow and deterministic: among an entity's document clauses, find clauses
that state a **renewal date**, and when the stated dates disagree, produce a
*conflict claim* that names both values, cites both clauses, and asserts that
no single date can be given.

The slice covers one conflict class (renewal dates in documents). That is the
honest scope, not a general contradiction detector; growing it is driven by
the eval (synthetic conflicting cases, spec 0022).
"""

from __future__ import annotations

import re

from tessera.grounding import Claim, EvidenceRecord

# "the Agreement auto-renews annually on 1 August" / "renews ... on 1 February"
RENEWAL_DATE = re.compile(r"renews\b.*?\bon (\d{1,2} [A-Z][a-z]+)", re.DOTALL)


def renewal_date_of(record: EvidenceRecord) -> str | None:
    """The renewal date a clause states, if it states one."""
    match = RENEWAL_DATE.search(record.text)
    return match.group(1) if match else None


def find_renewal_conflict(clauses: list[EvidenceRecord]) -> Claim | None:
    """A conflict claim when the clauses disagree on the renewal date.

    Returns ``None`` when there is no conflict (zero or one distinct stated
    date). With a conflict, the claim cites **every** date-stating clause, so
    the user can open both sides — disagreement is surfaced, not resolved.
    """
    dated = [(record, date) for record in clauses if (date := renewal_date_of(record))]
    distinct = sorted({date for _, date in dated})
    if len(distinct) < 2:
        return None

    sides = "; ".join(f"'{date}' ({record.origin.source})" for record, date in dated)
    return Claim(
        text=(
            f"Conflict: the cited documents disagree on the renewal date — "
            f"{sides}. No single renewal date can be asserted."
        ),
        support=tuple(record for record, _ in dated),
    )
