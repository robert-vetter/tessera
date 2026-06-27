"""The DevEx synthetic battery: deterministic, data-derived, floor-gated."""

from __future__ import annotations

import pytest

from tessera.devex.knowledge import build_devex_graph, build_devex_kb
from tessera.devex.synthetic import generate_cases
from tessera.eval.harness import run_eval
from tessera.graph import KnowledgeGraph
from tessera.grounding import KnowledgeBase


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_devex_graph()


@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    return build_devex_kb()


def test_battery_is_deterministic(graph: KnowledgeGraph, kb: KnowledgeBase) -> None:
    first = generate_cases(graph, kb)
    second = generate_cases(graph, kb)
    assert [c.id for c in first] == [c.id for c in second]
    assert [c.question for c in first] == [c.question for c in second]


def test_battery_composition(graph: KnowledgeGraph, kb: KnowledgeBase) -> None:
    """Exact composition over the current corpus — changes loudly: 6 RCA
    (failed runs), 8 refused premises (passed runs), 5 summaries, 2 unknown
    ids, 3 missing-evidence templates."""
    cases = generate_cases(graph, kb)
    assert len(cases) == 24
    assert sum(1 for c in cases if c.id.startswith("syn_devex_rca_")) == 6
    assert sum(1 for c in cases if c.id.startswith("syn_devex_refuse_passed_")) == 8
    assert sum(1 for c in cases if c.id.startswith("syn_devex_summary_")) == 5
    assert sum(1 for c in cases if c.kind == "refuse") == 13


def test_expectations_are_data_derived(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    """Every expected-support id exists in the graph (ADR 0007: derived from
    data, not echoed from engine output)."""
    node_ids = {n.id for n in graph.nodes}
    for case in generate_cases(graph, kb):
        assert set(case.expected_support) <= node_ids, case.id


def test_rca_cases_expect_the_error_chunks(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    cases = {c.id: c for c in generate_cases(graph, kb)}
    flagship = cases["syn_devex_rca_R-1042"]
    assert "run_R-1042:chunk5" in flagship.expected_support
    assert flagship.expected_facts == ("status failed (failing job integration-tests)",)


def test_unreferenced_pr_case_expects_no_ticket(
    graph: KnowledgeGraph, kb: KnowledgeBase
) -> None:
    cases = {c.id: c for c in generate_cases(graph, kb)}
    pr205 = cases["syn_devex_summary_PR-205"]
    assert not any(s.startswith("Ticket:") for s in pr205.expected_support)
    assert pr205.expected_facts == ()
    pr201 = cases["syn_devex_summary_PR-201"]
    assert "Ticket:DEVEX-204" in pr201.expected_support


def test_synthetic_verticals_floor_holds_and_coverage_loop_is_closed() -> None:
    """The two synthetic verticals scored by the same harness; faithfulness 1.0
    everywhere; and the Phase 3 coverage gap (the named notif-svc miss, 0.917)
    is closed by the declared catalog alias (spec 0036). The real GitHub
    Actions battery is measured by the same harness too (Milestone 5); its own
    numbers are pinned in test_github_actions_battery."""
    report = run_eval()
    by_name = {b.name: b for b in report.batteries}
    assert set(by_name) == {"business", "devex", "github_actions"}
    assert report.floor_holds  # faithfulness is 1.0 on every battery, always
    business, devex = by_name["business"], by_name["devex"]
    assert business.faithfulness == 1.0 and business.synthetic_faithfulness == 1.0
    assert devex.faithfulness == 1.0 and devex.synthetic_faithfulness == 1.0
    # Milestone 7 added the checkout-svc ER recall miss (gold case 09): offline,
    # difflib leaves checkout-svc unresolved, so the on-call is not surfaced — a
    # faithful PARTIAL, so faithfulness stays 1.0 while coverage/quality read the
    # recorded miss. Embeddings close it online (spec 0066); CI keeps the miss.
    assert devex.coverage == 0.95  # 19/20 — the checkout-svc on-call is uncited
    assert devex.quality == pytest.approx(8 / 9)  # gold case 09 misses offline
