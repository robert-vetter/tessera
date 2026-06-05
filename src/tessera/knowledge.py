"""Demo knowledge for the conversational surface — now built from *ingested* data.

Phase 0 hardcoded its evidence here. As of Phase 1 Unit 1 there is **no hardcoded
evidence**: the knowledge base is assembled by ingesting the synthetic,
SALT-shaped dataset through :mod:`tessera.sources.salt`, so every record carries a
real, traceable origin. What remains authored here is only the narrow demo
*question → claim* mapping, and each claim cites specific ingested records by id —
the claim text merely restates figures that literally appear in the cited rows.

Real question understanding and retrieval (so claims need not be pre-authored)
arrive in Unit 3; this module stays the thin, deterministic demo wiring until
then. Keeping it separate keeps the engine in :mod:`tessera.grounding` general and
vertical-neutral.
"""

from __future__ import annotations

from tessera.grounding import Claim, EvidenceRecord, Fact, KnowledgeBase
from tessera.sources.documents import DocumentSource
from tessera.sources.salt import SaltSyntheticSource

# The demo question is grounded in the spotlight customer of the ingested
# dataset: customer 0010000007, with two sales orders whose net values (EUR
# 20,000.00 + EUR 25,000.00) sum to the figure the answer reports.
DEMO_QUESTION = "What is the total net value of Müller Logistik GmbH's sales orders?"


def build_demo_kb() -> KnowledgeBase:
    """Ingest both sources and wire the narrow demo questions to ingested evidence.

    Structured (SALT-shaped) rows and unstructured document chunks arrive through
    the same ingestion path and live side by side in one knowledge base. The demo
    facts cite ingested records directly; a single claim that combines a row and a
    clause across the two sources is Unit 5 (it needs entity resolution first).
    """
    salt_records = tuple(SaltSyntheticSource().ingest())
    doc_records = tuple(DocumentSource().ingest())
    records = salt_records + doc_records

    by_id = {record.id: record for record in salt_records}
    customer = by_id["I_Customer:0010000007"]
    order_1 = by_id["I_SalesDocument:0000500001"]
    order_2 = by_id["I_SalesDocument:0000500002"]

    # The document-grounded fact cites the renewal clause of the master service
    # agreement. Selecting the chunk by content here is demo wiring, not query-time
    # retrieval (that arrives in Unit 3); the claim restates what the chunk says.
    renewal_clause = _find(
        doc_records, source_suffix="mueller_logistik_msa.md", contains="auto-renews"
    )

    facts = (
        Fact(
            keywords=("müller", "order"),
            claim=Claim(
                text=(
                    "Müller Logistik GmbH (customer 0010000007) has two sales "
                    "orders: 0000500001 and 0000500002."
                ),
                support=(customer, order_1, order_2),
            ),
        ),
        Fact(
            keywords=("müller", "total"),
            claim=Claim(
                text="The combined net value of those orders is EUR 45,000.00.",
                support=(order_1, order_2),
            ),
        ),
        Fact(
            keywords=("müller", "renew"),
            claim=Claim(
                text=(
                    "Müller Logistik's master service agreement auto-renews "
                    "annually on 1 August."
                ),
                support=(renewal_clause,),
            ),
        ),
    )
    return KnowledgeBase(records=records, facts=facts)


def _find(
    records: tuple[EvidenceRecord, ...], *, source_suffix: str, contains: str
) -> EvidenceRecord:
    """Return the one ingested record from a given source whose text contains
    ``contains``. Raises if absent, so a drifted corpus fails loudly at build."""
    for record in records:
        if record.origin.source.endswith(source_suffix) and contains in record.text:
            return record
    raise LookupError(f"no chunk of {source_suffix!r} contains {contains!r}")


DEMO_KB = build_demo_kb()
