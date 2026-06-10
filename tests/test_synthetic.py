"""The synthetic battery: deterministic, data-derived, honestly filtered."""

import pytest

from tessera.eval.harness import run_eval
from tessera.eval.synthetic import generate_cases
from tessera.graph import KnowledgeGraph
from tessera.grounding import KnowledgeBase
from tessera.knowledge import DEMO_KB, build_demo_graph


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_demo_graph()


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return DEMO_KB


def test_battery_is_deterministic(graph: KnowledgeGraph, kb: KnowledgeBase) -> None:
    first = generate_cases(graph, kb)
    second = generate_cases(graph, kb)
    assert [c.id for c in first] == [c.id for c in second]
    assert [c.question for c in first] == [c.question for c in second]


def test_battery_composition(graph: KnowledgeGraph, kb: KnowledgeBase) -> None:
    """Exact composition of the battery over the current data — changes loudly."""
    cases = generate_cases(graph, kb)
    by_kind = {c.id.split("_")[1] for c in cases}
    assert by_kind == {"lookup", "aggregate", "compare", "superlative", "refuse"}
    assert len(cases) == 51
    assert sum(1 for c in cases if c.kind == "refuse") == 7


def test_expectations_are_data_derived(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """Aggregate expectations carry record ids that exist in the graph — the
    generator derives them from data, not from engine output (ADR 0007)."""
    node_ids = {n.id for n in graph.nodes}
    for case in generate_cases(graph, kb):
        assert set(case.expected_support) <= node_ids


def test_ambiguous_family_not_generated_as_answerable(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """The deliberately unresolved Globex variant family is inherently
    ambiguous: it appears only as refusal cases, never as answerable ones."""
    for case in generate_cases(graph, kb):
        if case.kind == "answer":
            assert "globex" not in case.question.lower()


def test_missing_evidence_templates_are_vocabulary_checked(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """The zeppelin template shares a corpus token and must be filtered out —
    proof the vocabulary check is active, not decorative."""
    questions = {c.question for c in generate_cases(graph, kb)}
    assert "What colour is the sky?" in questions
    assert "Do we operate a zeppelin fleet?" not in questions


def test_synthetic_floor_holds_end_to_end() -> None:
    """The full battery runs through the harness with the faithfulness floor."""
    report = run_eval()
    assert report.synthetic_case_count > 40
    assert report.synthetic_faithfulness == 1.0
    assert report.floor_holds
