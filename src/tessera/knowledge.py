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

from tessera.grounding import Claim, Fact, KnowledgeBase
from tessera.sources.salt import SaltSyntheticSource

# The demo question is grounded in the spotlight customer of the ingested
# dataset: customer 0010000007, with two sales orders whose net values (EUR
# 20,000.00 + EUR 25,000.00) sum to the figure the answer reports.
DEMO_QUESTION = "What is the total net value of Müller Logistik GmbH's sales orders?"


def build_demo_kb() -> KnowledgeBase:
    """Ingest the dataset and wire the narrow demo question to ingested evidence."""
    records = tuple(SaltSyntheticSource().ingest())
    by_id = {record.id: record for record in records}

    customer = by_id["I_Customer:0010000007"]
    order_1 = by_id["I_SalesDocument:0000500001"]
    order_2 = by_id["I_SalesDocument:0000500002"]

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
    )
    return KnowledgeBase(records=records, facts=facts)


DEMO_KB = build_demo_kb()
