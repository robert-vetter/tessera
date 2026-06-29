"""Routing: the right question reaches the right engine, explainably."""

import pytest

from tessera.business.cli import main
from tessera.business.knowledge import DEMO_KB, build_demo_graph
from tessera.business.routing import classify, route
from tessera.graph import KnowledgeGraph
from tessera.grounding import REFUSAL_MESSAGE, KnowledgeBase


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_demo_graph()


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return DEMO_KB


def test_two_entities_route_multi(graph: KnowledgeGraph) -> None:
    decision = classify("Compare Müller Logistik and Nordwind Logistik.", graph)
    assert decision.kind == "multi"
    assert "Mueller Logistik Gmbh" in decision.reason


def test_superlative_routes_multi(graph: KnowledgeGraph) -> None:
    decision = classify("Which entity has the highest total in EUR?", graph)
    assert decision.kind == "multi"
    assert "ranking" in decision.reason


def test_one_entity_routes_compose(graph: KnowledgeGraph) -> None:
    decision = classify("Summarise Müller Logistik.", graph)
    assert decision.kind == "entity"
    assert "Mueller Logistik Gmbh" in decision.reason


def test_no_entity_routes_lookup(graph: KnowledgeGraph) -> None:
    decision = classify("When does the service agreement renew?", graph)
    assert decision.kind == "lookup"


def test_bare_ambiguous_term_routes_to_compose_and_refuses(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """A bare token shared by ≥2 distinct entities (e.g. "Logistik") names no
    single entity, but resolving it ties across firms. The router defers to
    compose's resolver and refuses as ambiguous rather than lexically grounding it
    (spec 0088 — the closed Milestone-11 business/05 divergence)."""
    decision = classify("Logistik", graph)
    assert decision.kind == "entity"
    assert "ambiguous" in decision.reason
    # Both tied firms are named in the reason, once each (no duplicate label).
    assert "Mueller Logistik Gmbh" in decision.reason
    assert "Nordwind Logistik GmbH" in decision.reason

    _, answer = route("Logistik", graph, kb)
    assert not answer.is_grounded
    assert "Ambiguous" in (answer.refusal or "")


def test_non_ambiguous_single_term_still_grounds_via_lookup(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """The alignment does not over-refuse: a term that does not tie across entities
    still routes to lexical lookup and grounds when the corpus supports it (here a
    distinctive content word from the agreements)."""
    decision, answer = route("renewal", graph, kb)
    assert decision.kind == "lookup"
    assert answer.is_grounded


@pytest.mark.parametrize(
    "question",
    [
        "What services does Logistik provide?",
        "Who are our Iberia contacts?",
        "Tell me about Kontor's operations.",
    ],
)
def test_content_question_with_ambiguous_token_still_routes_to_lookup(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """A *content* question that merely CONTAINS an ambiguous entity token must not
    be over-refused as a bare ambiguous reference: the matched run covers little of
    the question, so it stays on the lookup path (regression pins for the cases the
    spec-0088 pre-merge adversarial review surfaced — grounding a real lookup is the
    correct behaviour, not a false ambiguity refusal)."""
    decision = classify(question, graph)
    assert decision.kind == "lookup", decision.reason


def test_routed_multi_answer_is_grounded(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    decision, answer = route(
        "Compare Müller Logistik and Nordwind Logistik totals.", graph, kb
    )
    assert decision.kind == "multi"
    assert answer.is_grounded
    assert "exceeds" in answer.render()


def test_routed_entity_answer_is_grounded(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    decision, answer = route("Summarise Müller Logistik.", graph, kb)
    assert decision.kind == "entity"
    assert answer.is_grounded
    assert "is one resolved entity" in answer.render()


def test_routed_unanswerable_refuses(graph: KnowledgeGraph, kb: KnowledgeBase) -> None:
    decision, answer = route("What colour is the sky?", graph, kb)
    assert decision.kind == "lookup"
    assert not answer.is_grounded
    assert answer.refusal == REFUSAL_MESSAGE


def test_cli_prints_route_and_answer(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["Compare Müller Logistik and Nordwind Logistik totals."])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[route: multi" in out
    assert "exceeds" in out


def test_cli_engine_override(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["Summarise Müller Logistik.", "--engine", "retrieve"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[route:" not in out  # forced path skips the router
