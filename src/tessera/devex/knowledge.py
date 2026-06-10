"""Assemble the DevEx knowledge base and graph from the ingested corpus.

The DevEx counterpart to :mod:`tessera.business.knowledge`, built with the **same,
unchanged** engine machinery (spec 0028): nodes wrap ingested records,
foreign keys become structural edges, then the additive resolution layer
asserts which catalog/on-call names co-refer and the mention pass links log
and diff chunks to the services they name. Log chunks and diff hunks carry
the engine's ``document`` kind — "document" means *unstructured chunk node*
(ADR 0008); what file family a chunk came from stays visible in its origin.

The resolution outcomes on this corpus are measured, not assumed: the
catalog↔on-call variants for payments/auth/search/inventory merge at the
0.85 threshold. Phase 3 left two abbreviations unresolved as *named* recall
misses (spec 0026); the eval measured ``notif-svc`` (similarity 0.429) as
the 0.917 coverage gap, and the catalog now closes it with a **declared
alias** asserted here as an ordinary, reversible :class:`Resolution`
(spec 0036 / ADR 0010). ``checkout-svc`` (0.846) stays undeclared and
unresolved — aliases only fix what someone declares.
"""

from __future__ import annotations

from tessera.graph import Edge, KnowledgeGraph, Node, Resolution
from tessera.grounding import KnowledgeBase
from tessera.resolution import DEFAULT_RESOLUTION_THRESHOLD, normalize
from tessera.sources.devex import DevExSource

# The kinds that arrive as unstructured chunks (and so participate in the
# engine's document-mention linking).
_CHUNK_LOCATOR_KINDS = frozenset({"log-span", "diff-hunk"})

DEMO_QUESTION = "Why did run R-1042 fail?"


def build_devex_kb() -> KnowledgeBase:
    """All DevEx records as one retrievable knowledge base."""
    return KnowledgeBase(records=tuple(DevExSource().ingest()))


def build_devex_graph(
    threshold: float = DEFAULT_RESOLUTION_THRESHOLD,
) -> KnowledgeGraph:
    """One graph over all eight DevEx source shapes, resolved and linked."""
    source = DevExSource()
    org_names = source.org_names()
    node_attrs = source.node_attributes()

    graph = KnowledgeGraph()
    for record in source.ingest():
        if record.origin.locator.kind in _CHUNK_LOCATOR_KINDS:
            kind = "document"
        else:
            kind = record.id.split(":", 1)[0]  # the table name
        graph.add_node(
            Node(
                record=record,
                kind=kind,
                name=org_names.get(record.id),
                attributes=node_attrs.get(record.id, ()),
            )
        )

    for src, dst, relation in source.structural_edges():
        graph.add_edge(Edge(src=src, dst=dst, relation=relation))

    graph.resolve_entities(threshold)
    _assert_declared_aliases(graph, source.declared_aliases())
    graph.link_document_mentions()
    return graph


def _assert_declared_aliases(
    graph: KnowledgeGraph, declared: dict[str, tuple[str, ...]]
) -> None:
    """Assert same-entity for every name-bearing node a catalog alias names.

    Deliberately vertical-side (the engine stays untouched until a second
    vertical needs alias data — spec 0036) and deliberately *exact*: an alias
    matches by normalized equality, never similarity, so a declaration cannot
    transitively bridge two distinct services. Each assertion is an ordinary
    additive :class:`~tessera.graph.Resolution` — confidence 1.0 because it is
    declared catalog data, with a reason naming the declaration — so it stays
    inspectable and reversible like every other merge decision.
    """
    for component_id, aliases in sorted(declared.items()):
        for alias in aliases:
            needle = normalize(alias)
            for node in graph.name_nodes():
                assert node.name is not None
                if node.id != component_id and normalize(node.name) == needle:
                    graph.add_resolution(
                        Resolution(
                            node_a=component_id,
                            node_b=node.id,
                            score=1.0,
                            confidence=1.0,
                            reason=(
                                f"declared catalog alias: {alias!r} is listed "
                                f"for {component_id} in components.csv"
                            ),
                        )
                    )
