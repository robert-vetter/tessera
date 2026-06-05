"""Assemble the demo knowledge base from both ingested sources.

As of Phase 1 Unit 3 there is **no hand-authored knowledge** here at all: this
module just ingests the structured (SALT-shaped) and unstructured (document)
sources and hands their records to the knowledge base. Answering is done by
*retrieval* over those records (:mod:`tessera.retrieval`) — the question-to-claim
map and every precomputed claim are gone. Keeping assembly here keeps the engine
in :mod:`tessera.grounding` general and vertical-neutral.
"""

from __future__ import annotations

from tessera.grounding import KnowledgeBase
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


DEMO_KB = build_demo_kb()
