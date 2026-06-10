"""The measured batteries — the one eval module that names verticals.

Wiring, not internals (ADR 0009): scoring never branches on a vertical; this
module binds each vertical's graph/KB builders, engine dispatch, and
synthetic generator into a :class:`~tessera.eval.battery.Battery`. Adding a
vertical to the eval = adding one entry here (plus its gold directory). The
explicit tuple is deliberate — the set of measured verticals should be
readable in one place, and a battery cannot go silently missing.
"""

from __future__ import annotations

from pathlib import Path

from tessera.eval.battery import Battery, GoldCase
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, KnowledgeBase

GOLD_ROOT = Path(__file__).resolve().parents[3] / "eval" / "gold"


def _business_answer(
    case: GoldCase, graph: KnowledgeGraph, kb: KnowledgeBase
) -> Answer:
    from tessera.composition import compose
    from tessera.retrieval import answer as retrieve_answer
    from tessera.routing import route

    if case.engine == "compose":
        return compose(case.question, graph)
    if case.engine == "route":
        return route(case.question, graph, kb)[1]
    return retrieve_answer(case.question, kb)


def business_battery() -> Battery:
    from tessera.eval.synthetic import generate_cases
    from tessera.knowledge import build_demo_graph, build_demo_kb

    return Battery(
        name="business",
        gold_dir=GOLD_ROOT / "business",
        build_graph=build_demo_graph,
        build_kb=build_demo_kb,
        answer=_business_answer,
        synthetic=generate_cases,
    )


def batteries() -> tuple[Battery, ...]:
    """Every measured vertical. The DevEx battery lands in Unit 8 (spec
    0033); until then the tuple is honest about what is measured."""
    return (business_battery(),)
