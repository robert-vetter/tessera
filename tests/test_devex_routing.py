"""The DevEx routed door: explainable dispatch, working demo (spec 0031)."""

from __future__ import annotations

import pytest

from tessera.devex.cli import main
from tessera.devex.knowledge import build_devex_graph, build_devex_kb
from tessera.devex.routing import classify, route
from tessera.grounding import REFUSAL_MESSAGE


def test_classify_run_pr_and_lookup() -> None:
    assert classify("Why did run R-1042 fail?").kind == "rca"
    assert classify("What does PR-201 change?").kind == "summary"
    assert classify("Who is on call for payments-service?").kind == "lookup"
    # A run is the more specific subject when both are named (recorded rule).
    assert classify("Did PR-201 break run R-1042?").kind == "rca"


def test_every_route_carries_a_reason() -> None:
    for question in (
        "Why did run R-1042 fail?",
        "What does PR-201 change?",
        "Who owns checkout?",
    ):
        decision = classify(question)
        assert decision.reason


def test_route_dispatches_and_lookup_refuses_out_of_corpus() -> None:
    graph = build_devex_graph()
    kb = build_devex_kb()
    decision, answer = route("Why did run R-1042 fail?", graph, kb)
    assert decision.kind == "rca" and answer.is_grounded
    decision, answer = route("What colour is the sky?", graph, kb)
    assert decision.kind == "lookup"
    assert answer.refusal == REFUSAL_MESSAGE


def test_lookup_surfaces_oncall_evidence() -> None:
    """The lookup path serves catalog/on-call questions as far as lexical
    retrieval can — here the exact-named payments row is retrievable."""
    _, answer = route(
        "Who is on call for the payments service?",
        build_devex_graph(),
        build_devex_kb(),
    )
    assert answer.is_grounded
    rendered = answer.render()
    assert "Dana Petrov" in rendered


def test_cli_demo_explains_route_and_shows_provenance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "[route: rca" in out
    assert "Recurring failure:" in out
    assert "devex_synthetic/logs/run_R-1042.log" in out
    assert "↳" in out  # claim-level provenance rendered


def test_cli_engine_override(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["What does PR-201 change?", "--engine", "summary"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Motivating ticket:" in out
    assert "[route:" not in out  # forced path skips routing


def test_cli_refuses_unsupported(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["What colour is the sky?"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert REFUSAL_MESSAGE in out
