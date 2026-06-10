"""Change summaries: diff-grounded, ticket-linked, verifier-checked (spec 0030)."""

from __future__ import annotations

import pytest

from tessera.devex.knowledge import build_devex_graph
from tessera.devex.summaries import NO_PR_REFUSAL, summarize_change
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Claim


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_devex_graph()


def _nodes(graph: KnowledgeGraph) -> dict[str, Node]:
    return {node.id: node for node in graph.nodes}


def test_pr201_summary_ties_diff_to_its_ticket(graph: KnowledgeGraph) -> None:
    answer = summarize_change("What does PR-201 actually change?", graph)
    assert answer.is_grounded
    texts = [claim.text for claim in answer.claims]

    # Metadata row, then the diff itself — all three hunks, verbatim.
    assert texts[0].startswith('PR PR-201: "Add retry with backoff')
    hunks = [t for t in texts if t.startswith("diff --git ")]
    assert len(hunks) == 3
    assert any("src/payments/db_client.py" in t and "for attempt" in t for t in hunks)

    # The tie to the motivating ticket: a verifiable link claim + the ticket.
    links = [t for t in texts if t.startswith("Motivating ticket:")]
    assert links == [
        'Motivating ticket: "DEVEX-204" appears in '
        "'devex_synthetic/prs.csv' and 'devex_synthetic/tickets.csv'."
    ]
    assert any(t.startswith("Ticket DEVEX-204") for t in texts)


def test_every_summary_claim_passes_the_faithfulness_verifier(
    graph: KnowledgeGraph,
) -> None:
    nodes = _nodes(graph)
    for pr in ("PR-188", "PR-190", "PR-198", "PR-201", "PR-205"):
        answer = summarize_change(f"What does {pr} change?", graph)
        assert answer.is_grounded, pr
        for claim in answer.claims:
            assert is_supported(claim, nodes, graph), (pr, claim.text)


def test_unreferenced_pr_gets_no_invented_ticket(graph: KnowledgeGraph) -> None:
    """PR-205 deliberately cites no ticket (spec 0026): its summary is the
    PR row + diff, and nothing more."""
    answer = summarize_change("What does PR-205 change?", graph)
    assert answer.is_grounded
    texts = [claim.text for claim in answer.claims]
    assert not any(t.startswith("Motivating ticket:") for t in texts)
    assert not any(t.startswith("Ticket ") for t in texts)
    assert any(t.startswith("diff --git ") for t in texts)


def test_tampered_link_claim_is_caught(graph: KnowledgeGraph) -> None:
    nodes = _nodes(graph)
    answer = summarize_change("What does PR-201 change?", graph)
    real = next(c for c in answer.claims if c.text.startswith("Motivating ticket:"))
    assert is_supported(real, nodes, graph)
    tampered = Claim(
        text=real.text.replace("DEVEX-204", "DEVEX-209"), support=real.support
    )
    assert not is_supported(tampered, nodes, graph)


def test_unknown_pr_is_refused_by_name(graph: KnowledgeGraph) -> None:
    answer = summarize_change("What does PR-999 change?", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "PR-999" in answer.refusal


def test_question_without_a_pr_is_refused(graph: KnowledgeGraph) -> None:
    answer = summarize_change("What changed lately?", graph)
    assert answer.refusal == NO_PR_REFUSAL
