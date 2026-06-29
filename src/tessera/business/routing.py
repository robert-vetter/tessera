"""Business question routing: decide which answer path a question needs.

The router distinguishes a simple lookup from a question that needs one-entity
cross-source composition or genuine multi-step reasoning (Phase 2 roadmap).
It is deterministic and rule-based (ADR 0006), and every routing decision
carries a human-readable *reason* via the shared :class:`tessera.routing.Route`
contract. Routing never invents an answer path: a misrouted or unanswerable
question falls through to a path that refuses honestly rather than guessing.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from tessera.business.composition import compose, resolve_entity
from tessera.business.reasoning import find_named_entities, mentions_superlative, reason
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, KnowledgeBase
from tessera.resolution import normalize
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route

# A bare ambiguous *entity reference* (refuse, like compose) is distinguished from
# a content question that merely *contains* an ambiguous entity token (look it up)
# by how much of the QUESTION the matched name run covers. "Logistik" is ~all of
# its question (coverage 1.0); "What services does Logistik provide?" is mostly
# other words (coverage ~0.26). This mirrors find_named_entities's name-coverage
# ratio, applied to the question side — the guard the pre-merge adversarial review
# (spec 0088) showed the bare resolve_entity tie needs to avoid over-refusing
# legitimate lookups (e.g. "Who are our Iberia contacts?").
AMBIGUOUS_QUESTION_RATIO = 0.6


def _question_coverage(question: str, candidates: tuple[str, ...]) -> float:
    """Fraction of the normalized question covered by its longest common run with
    any tied candidate name — high only when the question *is* the entity token."""
    q = normalize(question)
    if not q:
        return 0.0
    best = 0
    for candidate in candidates:
        name = normalize(candidate)
        run = (
            SequenceMatcher(None, q, name)
            .find_longest_match(0, len(q), 0, len(name))
            .size
        )
        best = max(best, run)
    return best / len(q)


def classify(question: str, graph: KnowledgeGraph) -> Route:
    """Classify a question by what answering it would take.

    - Two or more named entities, or a superlative phrasing → multi-step
      reasoning (compare / ranking).
    - Exactly one named entity → one-entity cross-source composition.
    - A bare term that names no single entity but *is itself* an ambiguous entity
      reference (ties across ≥2 distinct entities under ``compose``'s own resolver,
      and the tied name run covers most of the question) → the compose path, which
      refuses as ambiguous rather than guessing. This defers to ``resolve_entity``
      so the router and ``compose`` agree on ambiguity by construction (spec 0088),
      closing the Milestone-11 `business/05` divergence: grounding a bare shared
      token (e.g. "Logistik", which ties Müller Logistik and Nordwind Logistik) as
      if unambiguous is the weaker behaviour. The question-coverage guard keeps a
      *content* question that merely contains an ambiguous token (e.g. "What
      services does Logistik provide?") on the lookup path, where it grounds.
    - Otherwise → lexical lookup over all evidence (which refuses when nothing
      relevant exists).
    """
    entities = find_named_entities(question, graph)
    if len(entities) >= 2:
        names = ", ".join(e.name for e in entities)
        return Route(
            kind="multi",
            reason=f"names {len(entities)} entities ({names}) — multi-step",
        )
    if mentions_superlative(question):
        return Route(kind="multi", reason="asks for a ranking — multi-step")
    if len(entities) == 1:
        return Route(
            kind="entity",
            reason=f"names one entity ({entities[0].name}) — cross-source composition",
        )
    ambiguous = resolve_entity(question, graph)
    if (
        ambiguous.status == "ambiguous"
        and _question_coverage(question, ambiguous.candidates)
        >= AMBIGUOUS_QUESTION_RATIO
    ):
        # dict.fromkeys dedupes while preserving order: two distinct clusters can
        # share a display name (the split same-name firms), so the candidate list
        # may repeat a label — name each once in the reason.
        candidates = " and ".join(dict.fromkeys(ambiguous.candidates))
        return Route(
            kind="entity",
            reason=(
                f"ambiguous entity reference ({candidates}) — refuse to guess, "
                "as cross-source composition does"
            ),
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
