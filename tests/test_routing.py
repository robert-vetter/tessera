"""Routing: the right question reaches the right engine, explainably."""

import pytest

from tessera.cli import main
from tessera.graph import KnowledgeGraph
from tessera.grounding import REFUSAL_MESSAGE, KnowledgeBase
from tessera.knowledge import DEMO_KB, build_demo_graph
from tessera.routing import classify, route


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
