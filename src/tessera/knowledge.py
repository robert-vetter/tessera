"""Assemble the demo knowledge base from both ingested sources.

As of Phase 1 Unit 3 there is **no hand-authored knowledge** here at all: this
module just ingests the structured (SALT-shaped) and unstructured (document)
sources and hands their records to the knowledge base. Answering is done by
*retrieval* over those records (:mod:`tessera.retrieval`) — the question-to-claim
map and every precomputed claim are gone. Keeping assembly here keeps the engine
in :mod:`tessera.grounding` general and vertical-neutral.
"""

from __future__ import annotations

from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase
from tessera.resolution import DEFAULT_RESOLUTION_THRESHOLD
from tessera.sources.documents import DocumentSource
from tessera.sources.salt import SaltSyntheticSource

# A question that retrieves structured evidence (the spotlight customer's sales
# rows). Try also: "When does Müller Logistik's service agreement renew?" — which
# retrieves a document clause — or an unsupported question, for a refusal.
DEMO_QUESTION = "What are Müller Logistik's sales orders?"


def build_demo_kb() -> KnowledgeBase:
    """Ingest both sources into one knowledge base of origin-tagged records."""
    records = tuple(SaltSyntheticSource().ingest()) + tuple(DocumentSource().ingest())
    return KnowledgeBase(records=records)


def build_demo_graph(
    threshold: float = DEFAULT_RESOLUTION_THRESHOLD,
) -> KnowledgeGraph:
    """Assemble the knowledge graph: nodes from both sources, SALT structural
    edges, then the additive (non-destructive) resolution and document-mention
    layers. Answering over the graph is Unit 5 — not done here."""
    salt = SaltSyntheticSource()
    org_names = salt.org_names()

    graph = KnowledgeGraph()
    for record in salt.ingest():
        kind = record.id.split(":", 1)[0]  # the SALT table name
        graph.add_node(Node(record=record, kind=kind, name=org_names.get(record.id)))
    for record in DocumentSource().ingest():
        graph.add_node(Node(record=record, kind="document"))

    for src, dst, relation in salt.structural_edges():
        graph.add_edge(Edge(src=src, dst=dst, relation=relation))

    graph.resolve_entities(threshold)
    graph.link_document_mentions()
    return graph


DEMO_KB = build_demo_kb()
