"""Demo knowledge for the Phase 0 hello-world.

This is hardcoded, illustrative data — *not* real ingestion. It exists only so
the grounding engine has something to answer against end-to-end before Phase 1
brings real sources, a knowledge graph, and entity resolution. Keeping it in its
own module keeps the engine in :mod:`tessera.grounding` general and
vertical-neutral.

The demo mirrors the business example from ``docs/PROJECT_BRIEF.md``: a question
that needs more than one record to answer, with every claim traced to the rows
behind it. The claim text is precomputed for the skeleton; nothing here pretends
to compute over the data.
"""

from __future__ import annotations

from tessera.grounding import Claim, EvidenceRecord, Fact, KnowledgeBase

# --- Evidence -----------------------------------------------------------------
_ACME = EvidenceRecord(
    id="contracts.csv:2",
    source="contracts.csv, row 2",
    text="Acme Corp — annual value $120,000, auto-renews 2026-08-01.",
)
_GLOBEX = EvidenceRecord(
    id="contracts.csv:5",
    source="contracts.csv, row 5",
    text="Globex Inc — annual value $80,000, auto-renews 2026-09-15.",
)

# --- Facts (claim + the question keywords that trigger it) --------------------
_FACTS = (
    Fact(
        keywords=("auto-renew", "q3"),
        claim=Claim(
            text="Two contracts auto-renew in Q3 2026: Acme Corp and Globex Inc.",
            support=(_ACME, _GLOBEX),
        ),
    ),
    Fact(
        keywords=("combined", "value"),
        claim=Claim(
            text="Their combined annual value is $200,000.",
            support=(_ACME, _GLOBEX),
        ),
    ),
)

DEMO_KB = KnowledgeBase(records=(_ACME, _GLOBEX), facts=_FACTS)

# The hardcoded question the hello-world answers out of the box.
DEMO_QUESTION = (
    "Which contracts auto-renew in Q3 2026, and what is their combined annual value?"
)
