"""The DevEx graph: same machinery, measured resolution, intact guarantees.

These tests are the Unit 3 proof (spec 0028) that the engine's graph and
resolution layers generalize unchanged: cross-source service resolution
works on CI/tracker data exactly as it did on customer/address masters —
including its honesty properties (named misses stay unresolved; assertions
are reversible; raw records are never altered).
"""

from __future__ import annotations

import pytest

from tessera.devex.knowledge import build_devex_graph
from tessera.graph import KnowledgeGraph
from tessera.resolution import similarity
from tessera.sources.devex import DevExSource


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_devex_graph()


def _cluster_of(graph: KnowledgeGraph, node_id: str) -> frozenset[str]:
    return graph.entity_of(node_id)


# --- measured similarity ground truth (pinned, so drift is loud) ----------------


def test_variant_similarities_are_what_the_corpus_claims() -> None:
    assert similarity("payments-service", "Payments Service") == 1.0
    assert similarity("inventory-service", "inventory service") == 1.0
    assert similarity("search-service", "search-servce") == pytest.approx(
        0.960, abs=0.001
    )
    assert similarity("checkout-service", "checkout-svc") == pytest.approx(
        0.846, abs=0.001
    )
    assert similarity("notifications-service", "notif-svc") == pytest.approx(
        0.429, abs=0.001
    )


def test_distinct_services_stay_below_the_threshold() -> None:
    """The transitive over-merge guard (ADR 0004), re-measured on DevEx
    names: no two *different* services come close to the 0.85 threshold."""
    catalog = _catalog_names()
    worst = max(
        similarity(a, b) for i, a in enumerate(catalog) for b in catalog[i + 1 :]
    )
    assert worst < 0.80


def _catalog_names() -> list[str]:
    return [
        name
        for record_id, name in DevExSource().org_names().items()
        if record_id.startswith("Component:")
    ]


# --- resolution outcomes ----------------------------------------------------------


def test_oncall_variants_resolve_to_their_catalog_components(
    graph: KnowledgeGraph,
) -> None:
    for component, owner in [
        ("Component:SVC-PAY", "Owner:Payments Service"),
        ("Component:SVC-AUTH", "Owner:auth-service"),
        ("Component:SVC-SRCH", "Owner:search-servce"),
        ("Component:SVC-INV", "Owner:inventory service"),
    ]:
        assert owner in _cluster_of(graph, component), (component, owner)


def test_undeclared_abbreviation_stays_a_named_miss(graph: KnowledgeGraph) -> None:
    """checkout-svc (0.846) is deliberately NOT declared as an alias and stays
    unresolved — aliases only fix what someone declares (spec 0036/ADR 0010):
    the honest boundary of the mechanism, kept measurable."""
    assert _cluster_of(graph, "Owner:checkout-svc") == frozenset({"Owner:checkout-svc"})


def test_declared_alias_resolves_the_measured_miss(graph: KnowledgeGraph) -> None:
    """notif-svc (similarity 0.429 — pinned above) was Phase 3's measured
    coverage miss; the catalog's declared alias now resolves it, with a
    reason naming the declaration and confidence 1.0 (declared data, not an
    inference)."""
    assert "Owner:notif-svc" in _cluster_of(graph, "Component:SVC-NOTIF")
    (alias_resolution,) = [
        r for r in graph.resolutions if "declared catalog alias" in r.reason
    ]
    assert {alias_resolution.node_a, alias_resolution.node_b} == {
        "Component:SVC-NOTIF",
        "Owner:notif-svc",
    }
    assert alias_resolution.confidence == 1.0
    assert "'notif-svc'" in alias_resolution.reason


def test_alias_declaration_is_citable_evidence(graph: KnowledgeGraph) -> None:
    """The declaring catalog row itself states the alias, so a claim about
    the co-reference can cite the record that declares it."""
    assert 'alias "notif-svc"' in graph.node("Component:SVC-NOTIF").record.text


def test_different_services_never_merge(graph: KnowledgeGraph) -> None:
    payments = _cluster_of(graph, "Component:SVC-PAY")
    checkout = _cluster_of(graph, "Component:SVC-CHK")
    assert payments.isdisjoint(checkout)


def test_resolutions_carry_reason_and_confidence(graph: KnowledgeGraph) -> None:
    assert graph.resolutions
    for resolution in graph.resolutions:
        # Two assertion regimes (ADR 0010): similarity matches carry the
        # matched forms + score; declared aliases carry the declaration.
        assert (
            "name match" in resolution.reason
            or "declared catalog alias" in resolution.reason
        )
        assert 0.85 <= resolution.confidence <= 1.0


# --- structural edges ---------------------------------------------------------------


def test_run_traverses_to_its_component(graph: KnowledgeGraph) -> None:
    """R-1042 --executes--> PIPE-PAY --builds--> SVC-PAY: a question about a
    run can reach the service it concerns in two deterministic hops."""
    executes = [
        e for e in graph.edges if e.src == "Run:R-1042" and e.relation == "executes"
    ]
    assert [e.dst for e in executes] == ["Pipeline:PIPE-PAY"]
    builds = [
        e
        for e in graph.edges
        if e.src == "Pipeline:PIPE-PAY" and e.relation == "builds"
    ]
    assert [e.dst for e in builds] == ["Component:SVC-PAY"]


def test_tickets_concern_their_components(graph: KnowledgeGraph) -> None:
    payments_tickets = set(
        graph.sources_of(set(_cluster_of(graph, "Component:SVC-PAY")), "concerns")
    )
    assert payments_tickets == {"Ticket:DEVEX-187", "Ticket:DEVEX-204"}


def test_pr_motivation_edges(graph: KnowledgeGraph) -> None:
    motivated = {e.src: e.dst for e in graph.edges if e.relation == "motivated_by"}
    assert motivated["PR:PR-201"] == "Ticket:DEVEX-204"
    assert motivated["PR:PR-188"] == "Ticket:DEVEX-150"
    assert motivated["PR:PR-190"] == "Ticket:DEVEX-160"
    assert "PR:PR-205" not in motivated  # deliberately unreferenced (spec 0026)


def test_log_chunks_and_diff_hunks_link_to_run_and_pr(graph: KnowledgeGraph) -> None:
    log_chunks = graph.sources_of({"Run:R-1042"}, "log_of")
    assert log_chunks and all(c.startswith("run_R-1042:") for c in log_chunks)
    hunks = graph.sources_of({"PR:PR-201"}, "diff_of")
    assert sorted(hunks) == [
        "PR-201.diff:hunk1",
        "PR-201.diff:hunk2",
        "PR-201.diff:hunk3",
    ]


def test_run_attributes_expose_outcome(graph: KnowledgeGraph) -> None:
    failed = graph.node("Run:R-1042")
    assert failed.attr("status") == "failed"
    assert failed.attr("failed_job") == "integration-tests"
    passed = graph.node("Run:R-1041")
    assert passed.attr("status") == "passed"
    assert passed.attr("failed_job") == ""


# --- mentions + reversibility --------------------------------------------------------


def test_log_chunks_mention_the_services_they_name(graph: KnowledgeGraph) -> None:
    payments = _cluster_of(graph, "Component:SVC-PAY")
    mentioning_chunks = {m.chunk for m in graph.mentions_of(set(payments))}
    assert any(chunk.startswith("run_R-1042:") for chunk in mentioning_chunks)
    assert any(chunk.startswith("run_R-0987:") for chunk in mentioning_chunks)


def test_alias_resolution_is_reversible_like_any_other() -> None:
    """A declared alias is an ordinary additive assertion: withdrawing it
    re-splits the cluster and leaves the raw records untouched."""
    graph = build_devex_graph()
    for resolution in [
        r for r in graph.resolutions if "declared catalog alias" in r.reason
    ]:
        graph.remove_resolution(resolution)
    assert _cluster_of(graph, "Owner:notif-svc") == frozenset({"Owner:notif-svc"})


def test_resolution_withdrawal_resplits_without_data_loss() -> None:
    graph = build_devex_graph()
    payments = _cluster_of(graph, "Component:SVC-PAY")
    assert "Owner:Payments Service" in payments
    record_before = graph.node("Owner:Payments Service").record

    for resolution in [
        r
        for r in graph.resolutions
        if {r.node_a, r.node_b} == {"Component:SVC-PAY", "Owner:Payments Service"}
    ]:
        graph.remove_resolution(resolution)

    assert _cluster_of(graph, "Owner:Payments Service") == frozenset(
        {"Owner:Payments Service"}
    )
    assert graph.node("Owner:Payments Service").record == record_before
