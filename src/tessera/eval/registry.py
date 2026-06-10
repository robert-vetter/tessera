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
    from tessera.business.composition import compose
    from tessera.business.routing import route
    from tessera.retrieval import answer as retrieve_answer

    if case.engine == "compose":
        return compose(case.question, graph)
    if case.engine == "route":
        return route(case.question, graph, kb)[1]
    return retrieve_answer(case.question, kb)


def business_battery() -> Battery:
    from tessera.business.knowledge import build_demo_graph, build_demo_kb
    from tessera.business.synthetic import generate_cases

    return Battery(
        name="business",
        gold_dir=GOLD_ROOT / "business",
        build_graph=build_demo_graph,
        build_kb=build_demo_kb,
        answer=_business_answer,
        synthetic=generate_cases,
    )


def _devex_answer(case: GoldCase, graph: KnowledgeGraph, kb: KnowledgeBase) -> Answer:
    from tessera.devex.rca import explain_failure
    from tessera.devex.routing import route
    from tessera.devex.summaries import summarize_change
    from tessera.retrieval import answer as retrieve_answer

    if case.engine == "rca":
        return explain_failure(case.question, graph)
    if case.engine == "summary":
        return summarize_change(case.question, graph)
    if case.engine == "route":
        return route(case.question, graph, kb)[1]
    return retrieve_answer(case.question, kb)


def devex_battery() -> Battery:
    from tessera.devex.knowledge import build_devex_graph, build_devex_kb
    from tessera.devex.synthetic import generate_cases

    return Battery(
        name="devex",
        gold_dir=GOLD_ROOT / "devex",
        build_graph=build_devex_graph,
        build_kb=build_devex_kb,
        answer=_devex_answer,
        synthetic=generate_cases,
    )


def batteries() -> tuple[Battery, ...]:
    """Every measured vertical — the Phase 3 milestone in one line: two
    genuinely different verticals, one unchanged engine, both measured."""
    return (business_battery(), devex_battery())
