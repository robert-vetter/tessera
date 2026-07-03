"""Answer a question over an ingested directory (spec 0120).

A vertical-neutral answer layer built *on* the engine (like ``tessera/business``
— not in it): lexical retrieval by default, and an **entity lookup** when the
question names a declared display-name. The entity lookup is where the M9/M10
multi-field entity resolution earns its keep on foreign data: when a name
resolves to more than one distinct entity, the answer **refuses** ("ambiguous")
rather than fabricate a merged answer — the concrete "ambiguous names refuse"
contract. Every non-refusal claim is a verbatim record rendering with its
provenance; nothing is computed or paraphrased.
"""

from __future__ import annotations

import re

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Answer, Claim, KnowledgeBase
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route


def _norm(text: str) -> str:
    """Lowercase, non-alphanumeric → single spaces, padded — for whole-phrase
    name matching that will not fire on a substring of a larger word."""
    collapsed = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return f" {collapsed} "


def mentioned_names(question: str, display_names: set[str]) -> list[str]:
    """Declared display names that appear as a whole phrase in the question,
    longest first (so 'Santa Fe' wins over a hypothetical 'Fe')."""
    q = _norm(question)
    hits = [name for name in display_names if _norm(name) in q]
    return sorted(hits, key=lambda n: (-len(n), n))


def name_nodes_for(graph: KnowledgeGraph, name: str) -> list[Node]:
    target = _norm(name).strip()
    return [n for n in graph.name_nodes() if n.name and _norm(n.name).strip() == target]


def _entity_facts(graph: KnowledgeGraph, component: frozenset[str]) -> list[Claim]:
    """Verbatim, cited claims for a resolved entity: its own records plus every
    record joined to a component member by a structural edge (either direction),
    plus document chunks that mention it — each quoted, deterministically."""
    ids: set[str] = set(component)
    for edge in graph.edges:
        if edge.src in component:
            ids.add(edge.dst)
        if edge.dst in component:
            ids.add(edge.src)
    for mention in graph.mentions_of(set(component)):
        ids.add(mention.chunk)

    claims: list[Claim] = []
    for node_id in sorted(ids):
        try:
            node = graph.node(node_id)
        except KeyError:
            continue
        claims.append(Claim(text=node.record.text, support=(node.record,)))
    return claims


def _ambiguous_refusal(name: str, count: int) -> str:
    return (
        f'"{name}" is ambiguous — it names {count} distinct entities in this '
        "data (kept apart by entity resolution). Ask about one of them "
        "specifically (add a distinguishing detail)."
    )


def answer_dir(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase, display_names: set[str]
) -> tuple[Route, Answer]:
    """Route a directory question: entity lookup for a named entity (refusing on
    ambiguity), else lexical retrieval (refusing on zero overlap)."""
    names = mentioned_names(question, display_names)
    for name in names:
        nodes = name_nodes_for(graph, name)
        components = {graph.entity_of(node.id) for node in nodes}
        if len(components) > 1:
            route = Route(
                kind="entity",
                reason=f"names '{name}', which resolves to multiple entities",
            )
            return route, Answer(
                question=question,
                claims=(),
                refusal=_ambiguous_refusal(name, len(components)),
            )
        if len(components) == 1:
            route = Route(
                kind="entity",
                reason=f"names the entity '{name}' — its facts and links",
            )
            claims = _entity_facts(graph, next(iter(components)))
            return route, Answer(question=question, claims=tuple(claims), refusal=None)

    route = Route(
        kind="lookup",
        reason="no declared entity named — lexical lookup over the corpus",
    )
    return route, retrieve_answer(question, kb)
