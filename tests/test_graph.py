"""Tests for the knowledge-graph engine: clustering, reversibility, and that the
resolution layer never mutates the underlying records.
"""

from __future__ import annotations

from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import EvidenceRecord, Locator, Origin


def _name_node(node_id: str, name: str) -> Node:
    origin = Origin("test.csv", Locator.table_row("T", 1), "2026-06-05")
    rec = EvidenceRecord(id=node_id, origin=origin, text=name)
    return Node(record=rec, kind="I_Customer", name=name)


def _graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_node(_name_node("c1", "Müller Logistik GmbH"))
    g.add_node(_name_node("c2", "Mueller Logistik Gmbh"))  # variant of c1
    g.add_node(_name_node("c3", "Nordwind Logistik GmbH"))  # distinct firm
    return g


def test_resolution_clusters_variants_not_distinct_firms() -> None:
    g = _graph()
    g.resolve_entities()
    assert g.entity_of("c1") == g.entity_of("c2")  # variants merge
    assert "c3" not in g.entity_of("c1")  # distinct firm stays separate


def test_resolution_records_reason_and_confidence() -> None:
    g = _graph()
    g.resolve_entities()
    assert g.resolutions
    r = g.resolutions[0]
    assert r.reason
    assert 0.0 <= r.confidence <= 1.0


def test_resolution_is_reversible() -> None:
    g = _graph()
    g.resolve_entities()
    assert g.entity_of("c1") == g.entity_of("c2")
    g.remove_resolution(g.resolutions[0])  # withdraw the assertion
    assert g.entity_of("c1") != g.entity_of("c2")  # cluster re-splits


def test_resolution_is_non_destructive() -> None:
    g = _graph()
    before = {n.id: n.record for n in g.nodes}
    g.resolve_entities()
    after = {n.id: n.record for n in g.nodes}
    # The raw records are the very same objects, unmodified.
    assert before == after
    assert all(g.node(nid).record is rec for nid, rec in before.items())


def test_structural_edges_and_provenance_preserved() -> None:
    g = _graph()
    g.add_edge(Edge("c1", "c2", "related"))
    assert g.edges == (Edge("c1", "c2", "related"),)
    # Every node still carries its record's origin (provenance intact).
    assert all(n.record.origin.source for n in g.nodes)
