"""The routing contract: where a question was sent, and why — explainably.

Each vertical owns its own router (question shapes are per-vertical, ADR
0008): the business dispatch lives in :mod:`tessera.business.routing`, the
DevEx dispatch in :mod:`tessera.devex.routing`. What they share is the
discipline this module defines: every routing decision is a :class:`Route`
carrying a human-readable *reason* — routing is part of the answer's story,
so it must be as inspectable as the provenance itself — and a router never
invents an answer path: a misrouted or unanswerable question falls through
to a path that refuses honestly rather than guessing (ADR 0006).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    """Where a question was sent, and why."""

    kind: str  # a vertical's answer-path name, e.g. "multi" | "entity" | "lookup"
    reason: str
