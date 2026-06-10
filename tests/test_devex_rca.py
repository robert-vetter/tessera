"""Root-cause analysis: grounded hypotheses, verified claims, honest refusals.

The Unit 4 proof (spec 0029). The strongest test here runs the eval's own
verifier over every claim the RCA path emits — so Unit 8's battery cannot be
surprised: if RCA can say it, the verifier can check it.
"""

from __future__ import annotations

import pytest

from tessera.devex.knowledge import build_devex_graph
from tessera.devex.rca import NO_RUN_REFUSAL, explain_failure
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Answer, Claim


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_devex_graph()


def _nodes(graph: KnowledgeGraph) -> dict[str, Node]:
    return {node.id: node for node in graph.nodes}


def _claim_texts(answer: Answer) -> list[str]:
    return [claim.text for claim in answer.claims]


# --- the flagship question -----------------------------------------------------------


def test_r1042_failure_is_explained_and_linked_to_history(
    graph: KnowledgeGraph,
) -> None:
    answer = explain_failure("Why did run R-1042 fail?", graph)
    assert answer.is_grounded
    texts = _claim_texts(answer)

    # The outcome row and the failing log lines, verbatim.
    assert any("Run R-1042" in t and "status failed" in t for t in texts)
    assert any(
        "ERROR payments-service: TimeoutError: connection to payments-db" in t
        for t in texts
    )
    # Recurrence: the same signature in the EARLIER run R-0987's log.
    recurrences = [t for t in texts if t.startswith("Recurring failure:")]
    assert len(recurrences) == 1
    assert "logs/run_R-0987.log" in recurrences[0]
    assert "logs/run_R-1042.log" in recurrences[0]
    # The documented incident, linked and quoted.
    incidents = [t for t in texts if t.startswith("Documented incident:")]
    assert len(incidents) == 1
    assert "tickets.csv" in incidents[0]
    assert any("Ticket DEVEX-187" in t for t in texts)


def test_every_rca_claim_passes_the_faithfulness_verifier(
    graph: KnowledgeGraph,
) -> None:
    nodes = _nodes(graph)
    for question in (
        "Why did run R-1042 fail?",
        "Why did run R-0987 fail?",
        "Why did run R-1031 fail?",
        "Why did run R-1023 fail?",
        "Why did run R-1018 fail?",
        "Why did run R-1012 fail?",
    ):
        answer = explain_failure(question, graph)
        assert answer.is_grounded, question
        for claim in answer.claims:
            assert is_supported(claim, nodes, graph), (question, claim.text)


def test_tampered_recurrence_claim_is_caught(graph: KnowledgeGraph) -> None:
    """The adversarial check (ADR 0005 discipline): take the real recurrence
    claim, alter its quoted signature, and the verifier must reject it."""
    nodes = _nodes(graph)
    answer = explain_failure("Why did run R-1042 fail?", graph)
    real = next(c for c in answer.claims if c.text.startswith("Recurring failure:"))
    assert is_supported(real, nodes, graph)
    tampered = Claim(
        text=real.text.replace("timed out after 30s", "timed out after 31s"),
        support=real.support,
    )
    assert not is_supported(tampered, nodes, graph)


# --- recurrence honesty ---------------------------------------------------------


def test_first_occurrence_has_no_recurrence_claim(graph: KnowledgeGraph) -> None:
    """R-1023 is the FIRST search-replica failure: nothing is prior to it,
    so claiming recurrence would be fabrication. Its documented incident
    (DEVEX-231 quotes the signature) still surfaces."""
    texts = _claim_texts(explain_failure("Why did run R-1023 fail?", graph))
    assert not any(t.startswith("Recurring failure:") for t in texts)
    assert any(t.startswith("Documented incident:") for t in texts)


def test_second_occurrence_links_back(graph: KnowledgeGraph) -> None:
    texts = _claim_texts(explain_failure("Why did run R-1031 fail?", graph))
    recurrences = [t for t in texts if t.startswith("Recurring failure:")]
    assert len(recurrences) == 1
    assert "logs/run_R-1023.log" in recurrences[0]


def test_isolated_failures_get_no_history_claims(graph: KnowledgeGraph) -> None:
    """R-1018 (checkout) and R-1012 (auth) each failed once, with no ticket
    quoting their signatures: the answer is the run + its log lines, and
    nothing else — no invented history."""
    for run in ("R-1018", "R-1012"):
        texts = _claim_texts(explain_failure(f"Why did run {run} fail?", graph))
        assert not any(t.startswith("Recurring failure:") for t in texts), run
        assert not any(t.startswith("Documented incident:") for t in texts), run
        assert any("ERROR" in t for t in texts), run


# --- refusals -------------------------------------------------------------------


def test_passed_run_is_a_refused_premise(graph: KnowledgeGraph) -> None:
    answer = explain_failure("Why did run R-1041 fail?", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "did not fail" in answer.refusal


def test_unknown_run_is_refused_by_name(graph: KnowledgeGraph) -> None:
    answer = explain_failure("Why did run R-9999 fail?", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "R-9999" in answer.refusal


def test_question_without_a_run_is_refused(graph: KnowledgeGraph) -> None:
    answer = explain_failure("Why did the pipeline fail?", graph)
    assert answer.refusal == NO_RUN_REFUSAL
