"""Grade every method × attack × threat model into a scorecard (spec 0146).

Deterministic and offline: the same inputs produce byte-identical output,
so the committed scorecard can be pinned against a fresh run.

Reading order matters and is enforced by the renderer: the outside-tamperer
result comes first, because under that model the signature-based methods
detect everything and re-execution adds no detection power. The gap is a
property of the *issuer* model — where the party sealing the receipt is the
party whose honesty is in question.
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.conformance.attacks import ATTACKS, FAMILIES, Attack, base_bundles
from tessera.conformance.methods import (
    DETECTED,
    ISSUER,
    METHODS,
    MISSED,
    NOT_APPLICABLE,
    OUTSIDER,
    THREATS,
    Method,
)


@dataclass(frozen=True)
class Cell:
    """One graded (method, attack, threat) outcome."""

    method: str
    attack: str
    family: str
    threat: str
    outcome: str

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "attack": self.attack,
            "family": self.family,
            "threat": self.threat,
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class Scorecard:
    """The full grid plus the per-(method, threat, family) tallies."""

    cells: tuple[Cell, ...]

    def outcome(self, method: str, attack: str, threat: str) -> str:
        for cell in self.cells:
            if (
                cell.method == method
                and cell.attack == attack
                and cell.threat == threat
            ):
                return cell.outcome
        raise KeyError(f"no cell for {method}/{attack}/{threat}")

    def tally(
        self, method: str, threat: str, family: str | None = None
    ) -> tuple[int, int]:
        """(detected, applicable) — NOT-APPLICABLE never counts (ADR 0036)."""
        detected = applicable = 0
        for cell in self.cells:
            if cell.method != method or cell.threat != threat:
                continue
            if family is not None and cell.family != family:
                continue
            if cell.outcome == NOT_APPLICABLE:
                continue
            applicable += 1
            if cell.outcome == DETECTED:
                detected += 1
        return detected, applicable

    def to_dict(self) -> dict[str, object]:
        return {
            "benchmark": "tessera-verification-gap-1",
            "methods": [method.to_dict() for method in METHODS],
            "attacks": [attack.to_dict() for attack in ATTACKS],
            "threats": {
                OUTSIDER: (
                    "an attacker who does not hold the issuer's signing key "
                    "alters the receipt"
                ),
                ISSUER: (
                    "the forgery is produced inside the trust boundary and "
                    "re-attested with a legitimate key — the operative model "
                    "for an agent's own receipt"
                ),
            },
            "cells": [cell.to_dict() for cell in self.cells],
            "totals": {
                threat: {
                    method.key: {
                        "overall": list(self.tally(method.key, threat)),
                        **{
                            family: list(self.tally(method.key, threat, family))
                            for family in FAMILIES
                        },
                    }
                    for method in METHODS
                }
                for threat in THREATS
            },
        }


def _grade(
    method: Method,
    attack: Attack,
    base: dict[str, object],
    forged: dict[str, object],
    threat: str,
) -> Cell:
    if method.key in attack.not_applicable_to:
        outcome = NOT_APPLICABLE
    else:
        outcome = method.check(base, forged, threat)
        if outcome not in (DETECTED, MISSED):  # defensive: never a silent third state
            outcome = MISSED
    return Cell(
        method=method.key,
        attack=attack.key,
        family=attack.family,
        threat=threat,
        outcome=outcome,
    )


def run_benchmark() -> Scorecard:
    """Grade the whole grid. Pure, offline, deterministic.

    Each attack is forged **once** — a mutant depends only on its base, not
    on the method or threat model grading it — so the expensive part (deep
    copy + re-seal of a large bundle) runs 1× per attack rather than 1× per
    cell.
    """
    bases = base_bundles()
    forged = {attack.key: attack.forge(bases[attack.base]) for attack in ATTACKS}
    cells: list[Cell] = []
    for threat in THREATS:
        for attack in ATTACKS:
            base = bases[attack.base]
            for method in METHODS:
                cells.append(_grade(method, attack, base, forged[attack.key], threat))
    return Scorecard(cells=tuple(cells))


# --- rendering --------------------------------------------------------------------

_MARK = {DETECTED: "✓", MISSED: "✗", NOT_APPLICABLE: "–"}


def render_scorecard(card: Scorecard) -> str:
    lines = [
        "The Verification Gap — what each verification method detects",
        "",
        "Methods are OUR implementations of PUBLISHED methods, written to be",
        "as strong as their sources describe. No vendor is named or scored.",
        "",
    ]
    for threat in THREATS:
        if threat == OUTSIDER:
            lines.append("── Threat model 1: an OUTSIDE tamperer (no signing key) ──")
            lines.append(
                "   Signatures are sufficient here: any change moves the root and"
            )
            lines.append(
                "   cannot be re-attested. Re-execution adds no detection power."
            )
        else:
            lines.append(
                "── Threat model 2: the ISSUER itself (self-sealed, re-signed) ──"
            )
            lines.append("   The operative model for an agent's own receipt: the party")
            lines.append("   sealing it is the party whose honesty is in question.")
        lines.append("")
        header = f"   {'method':<24}" + "".join(f"{f[:9]:>11}" for f in FAMILIES)
        lines.append(header + f"{'TOTAL':>11}")
        for method in METHODS:
            row = f"   {method.key:<24}"
            for family in FAMILIES:
                detected, applicable = card.tally(method.key, threat, family)
                row += f"{f'{detected}/{applicable}':>11}"
            detected, applicable = card.tally(method.key, threat)
            row += f"{f'{detected}/{applicable}':>11}"
            lines.append(row)
        lines.append("")

    lines.append("── Per-attack detail (issuer model) ──")
    for family in FAMILIES:
        lines.append(f"   [{family}]")
        for attack in ATTACKS:
            if attack.family != family:
                continue
            marks = "".join(
                f"{_MARK[card.outcome(method.key, attack.key, ISSUER)]:>3}"
                for method in METHODS
            )
            lines.append(f"     {attack.key:<28}{marks}   {attack.description}")
    lines.append("")
    lines.append(
        "   columns: " + ", ".join(f"{i + 1}={m.key}" for i, m in enumerate(METHODS))
    )
    lines.append("   ✓ detected · ✗ missed · – not applicable (never scored)")
    return "\n".join(lines)
