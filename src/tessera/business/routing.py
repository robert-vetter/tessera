"""Business question routing: decide which answer path a question needs.

The router distinguishes a simple lookup from a question that needs one-entity
cross-source composition or genuine multi-step reasoning (Phase 2 roadmap).
It is deterministic and rule-based (ADR 0006), and every routing decision
carries a human-readable *reason* via the shared :class:`tessera.routing.Route`
contract. Routing never invents an answer path: a misrouted or unanswerable
question falls through to a path that refuses honestly rather than guessing.
"""

from __future__ import annotations

from tessera.business.composition import compose
from tessera.business.reasoning import SUPERLATIVE_WORDS, find_named_entities, reason
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, KnowledgeBase
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route


def classify(question: str, graph: KnowledgeGraph) -> Route:
    """Classify a question by what answering it would take.

    - Two or more named entities, or a superlative phrasing → multi-step
      reasoning (compare / ranking).
    - Exactly one named entity → one-entity cross-source composition.
    - Otherwise → lexical lookup over all evidence (which refuses when nothing
      relevant exists).
    """
    entities = find_named_entities(question, graph)
    lowered = question.lower()
    if len(entities) >= 2:
        names = ", ".join(e.name for e in entities)
        return Route(
            kind="multi",
            reason=f"names {len(entities)} entities ({names}) — multi-step",
        )
    if any(word in lowered for word in SUPERLATIVE_WORDS):
        return Route(kind="multi", reason="asks for a ranking — multi-step")
    if len(entities) == 1:
        return Route(
            kind="entity",
            reason=f"names one entity ({entities[0].name}) — cross-source composition",
        )
    return Route(kind="lookup", reason="no entity named — lexical lookup")


def route(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase
) -> tuple[Route, Answer]:
    """Classify, dispatch, and return both the route and the answer."""
    decision = classify(question, graph)
    if decision.kind == "multi":
        return decision, reason(question, graph)
    if decision.kind == "entity":
        return decision, compose(question, graph)
    return decision, retrieve_answer(question, kb)
