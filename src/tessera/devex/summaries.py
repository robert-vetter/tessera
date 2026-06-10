"""Change summaries: what a PR actually does, tied to the ticket behind it.

The second DevEx milestone behaviour (spec 0030): given *"what does PR-201
change?"*, surface the PR's metadata row, the diff hunks themselves (the
summary is built **from** the diff — no prose is synthesized about code the
claims could not cite), the motivating-ticket link as a verifiable
shared-fragment claim (the ticket id appears in both the PR row and the
ticket row), and the ticket's own text.

A PR that names no ticket (PR-205 in the corpus) gets a summary without a
link — honest omission, not invention. Unknown or unnamed PRs are refused
with the reason. Deterministic; no LLM (ADR 0006).
"""

from __future__ import annotations

import re

from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, Claim

PR_ID = re.compile(r"\bPR-\d{3,5}\b")

NO_PR_REFUSAL = (
    "I can't find a pull request in that question — name one, "
    "e.g. 'What does PR-201 change?'."
)


def _unknown_pr_refusal(pr_id: str) -> str:
    return f"There is no pull request {pr_id} in the knowledge graph."


def summarize_change(question: str, graph: KnowledgeGraph) -> Answer:
    """Answer "what does PR X change?" with grounded claims, or refuse."""
    match = PR_ID.search(question)
    if match is None:
        return Answer(question=question, claims=(), refusal=NO_PR_REFUSAL)
    pr_id = f"PR:{match.group(0)}"

    try:
        pr = graph.node(pr_id)
    except KeyError:
        return Answer(
            question=question,
            claims=(),
            refusal=_unknown_pr_refusal(match.group(0)),
        )

    # 1) The PR's metadata row — title, author, merge, description — verbatim.
    claims: list[Claim] = [Claim(text=pr.record.text, support=(pr.record,))]

    # 2) The diff itself, hunk by hunk: what the change actually touches.
    hunk_ids = sorted(graph.sources_of({pr_id}, "diff_of"))
    claims.extend(
        Claim(text=graph.node(hid).record.text, support=(graph.node(hid).record,))
        for hid in hunk_ids
    )

    # 3) The motivating ticket, when the PR names one (the structural edge
    #    extracted at ingestion): a verifiable cross-source link claim plus
    #    the ticket's own text. No edge -> no claim; nothing is invented.
    ticket_ids = [
        edge.dst
        for edge in graph.edges
        if edge.src == pr_id and edge.relation == "motivated_by"
    ]
    for ticket_id in sorted(ticket_ids):
        ticket = graph.node(ticket_id)
        ticket_ref = ticket_id.removeprefix("Ticket:")
        sources = sorted({pr.record.origin.source, ticket.record.origin.source})
        named = " and ".join(f"'{source}'" for source in sources)
        claims.append(
            Claim(
                text=f'Motivating ticket: "{ticket_ref}" appears in {named}.',
                support=(pr.record, ticket.record),
            )
        )
        claims.append(Claim(text=ticket.record.text, support=(ticket.record,)))

    return Answer(question=question, claims=tuple(claims), refusal=None)
