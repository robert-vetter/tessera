"""What the eval measures: gold cases, and the per-vertical battery bundle.

A :class:`Battery` is the unit of measurement (ADR 0009): everything the
harness needs to score one vertical — where its curated gold cases live, how
to build its graph and knowledge base, how a case's ``engine`` string maps to
that vertical's answer paths, and how its synthetic cases are enumerated.
The scoring machinery itself (:mod:`tessera.eval.harness`) stays a single,
shared, vertical-neutral function; verticals are *bound* in
:mod:`tessera.eval.registry`, never inside the internals.

:class:`GoldCase` lives here (it is what a battery's gold directory and
synthetic generator produce); :mod:`tessera.eval.harness` re-exports it for
compatibility.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.eval.metrics import ClaimShape
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, KnowledgeBase


@dataclass(frozen=True)
class GoldCase:
    """One evaluation case (curated gold, or generated synthetic).

    ``kind`` is ``"answer"`` or ``"refuse"``; ``engine`` names an answer path
    of the owning battery's vertical (interpreted by ``Battery.answer``).
    ``expected_support`` are the evidence ids a faithful answer should
    surface (coverage); ``expected_facts`` are substrings a correct answer
    must contain (quality).
    """

    id: str
    question: str
    engine: str
    kind: str
    expected_support: tuple[str, ...] = ()
    expected_facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Battery:
    """One vertical, as the eval harness sees it (ADR 0009).

    ``claim_shapes`` are the vertical's own claim grammars (ADR 0011),
    consulted by the verifier before the generic shapes — declared here so a
    battery's entire verification surface is explicit and readable.
    """

    name: str
    gold_dir: Path
    build_graph: Callable[[], KnowledgeGraph]
    build_kb: Callable[[], KnowledgeBase]
    answer: Callable[[GoldCase, KnowledgeGraph, KnowledgeBase], Answer]
    synthetic: Callable[[KnowledgeGraph, KnowledgeBase], list[GoldCase]]
    claim_shapes: tuple[ClaimShape, ...] = ()
