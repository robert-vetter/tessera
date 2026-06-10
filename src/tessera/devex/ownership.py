"""Service-ownership lookup: answer "who owns / is on call for X" from the graph.

The devex counterpart to the business vertical's entity resolution (spec
0036): a question naming a catalog service — by canonical name, by an
on-call variant the resolver merged, or by a **declared alias** — is
answered from the resolved entity's own records (the catalog row and the
on-call rows in its cluster), each claim a verbatim, cited snippet. This is
what turns a closed entity-resolution gap into a closed *coverage* gap: the
lexical retriever cannot know that ``notif-svc`` is ``notifications-service``,
but the graph now does.

Matching is whole-name normalized containment (never similarity), the best
match wins by needle length, and a tie between *distinct* entities is
refused as ambiguous rather than guessed — the same discipline as
``tessera.business.composition.resolve_entity``.
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, Claim
from tessera.resolution import normalize

NO_SERVICE_REFUSAL = (
    "I couldn't find a catalog service in that question — name one, "
    "e.g. 'Who is on call for payments-service?'."
)

# Claims are ordered catalog-row-first: the canonical identity, then who is on
# call for it, then anything else resolved into the entity.
_KIND_ORDER = {"Component": 0, "Owner": 1}


@dataclass(frozen=True)
class ServiceMatch:
    """The outcome of resolving a question to a service entity."""

    status: str  # "ok" | "none" | "ambiguous"
    cluster: frozenset[str] = frozenset()
    candidates: tuple[str, ...] = ()


def _needles(graph: KnowledgeGraph) -> list[tuple[str, str]]:
    """(normalized needle, node id) pairs a question can name a service by:
    every name-bearing node's name, plus every declared alias a catalog row
    exposes as an ``alias`` attribute."""
    pairs: list[tuple[str, str]] = []
    for node in graph.name_nodes():
        assert node.name is not None
        pairs.append((normalize(node.name), node.id))
        pairs.extend(
            (normalize(value), node.id)
            for key, value in node.attributes
            if key == "alias"
        )
    return pairs


def _display_name(graph: KnowledgeGraph, cluster: frozenset[str]) -> str:
    """The most complete member name; (len, name) tie-break for determinism."""
    names = [graph.node(nid).name for nid in cluster if graph.node(nid).name]
    return max(
        (n for n in names if n), key=lambda n: (len(n), n), default="(unnamed service)"
    )


def find_service(question: str, graph: KnowledgeGraph) -> ServiceMatch:
    """Resolve the question to one service entity by contained-name match."""
    q = normalize(question)
    best_by_cluster: dict[frozenset[str], int] = {}
    for needle, node_id in _needles(graph):
        if needle and needle in q:
            cluster = graph.entity_of(node_id)
            best_by_cluster[cluster] = max(best_by_cluster.get(cluster, 0), len(needle))
    if not best_by_cluster:
        return ServiceMatch(status="none")

    top = max(best_by_cluster.values())
    winners = [c for c, length in best_by_cluster.items() if length == top]
    if len(winners) > 1:
        labels = tuple(sorted(_display_name(graph, c) for c in winners))
        return ServiceMatch(status="ambiguous", candidates=labels)
    return ServiceMatch(status="ok", cluster=winners[0])


def service_lookup(question: str, graph: KnowledgeGraph) -> Answer:
    """Answer a service question from the resolved entity's records, or refuse."""
    match = find_service(question, graph)
    if match.status == "none":
        return Answer(question=question, claims=(), refusal=NO_SERVICE_REFUSAL)
    if match.status == "ambiguous":
        listed = ", ".join(f"'{name}'" for name in match.candidates)
        return Answer(
            question=question,
            claims=(),
            refusal=f"Ambiguous service reference — it could mean: {listed}.",
        )

    members = sorted(
        (graph.node(nid) for nid in match.cluster),
        key=lambda n: (_KIND_ORDER.get(n.kind, 2), n.id),
    )
    claims = tuple(
        Claim(text=node.record.text, support=(node.record,)) for node in members
    )
    return Answer(question=question, claims=claims, refusal=None)
