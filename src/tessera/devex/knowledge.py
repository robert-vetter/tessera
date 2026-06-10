"""Assemble the DevEx knowledge base and graph from the ingested corpus.

The DevEx counterpart to :mod:`tessera.knowledge`, built with the **same,
unchanged** engine machinery (spec 0028): nodes wrap ingested records,
foreign keys become structural edges, then the additive resolution layer
asserts which catalog/on-call names co-refer and the mention pass links log
and diff chunks to the services they name. Log chunks and diff hunks carry
the engine's ``document`` kind — "document" means *unstructured chunk node*
(ADR 0008); what file family a chunk came from stays visible in its origin.

The resolution outcomes on this corpus are measured, not assumed: the
catalog↔on-call variants for payments/auth/search/inventory merge at the
0.85 threshold; ``checkout-svc`` (similarity 0.846) and ``notif-svc``
(0.429) deliberately stay unresolved — the vertical's *named* recall misses
(spec 0026), left for the eval to see before anything "fixes" them.
"""

from __future__ import annotations

from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase
from tessera.resolution import DEFAULT_RESOLUTION_THRESHOLD
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
    graph.link_document_mentions()
    return graph
