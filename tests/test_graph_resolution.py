"""Proof tests for Unit 4 on the real demo graph (spec 0014, constraint #4):
known variants resolve to one entity with traceable reasons + confidence, a known
non-match stays separate, the merge is reversible, and a document links across
sources to its entity.
"""

from __future__ import annotations

from tessera.knowledge import build_demo_graph

MUELLER = "I_Customer:0010000007"
MUELLER_ADDR = "I_AddrOrgNamePostalAddress:A0007"
NORDWIND = "I_Customer:0010001007"
BAYERISCHE = "I_Customer:0010001019"


def test_bayerische_variants_resolve_to_one_entity() -> None:
    g = build_demo_graph()
    entity = g.entity_of(BAYERISCHE)
    customers = {x for x in entity if x.startswith("I_Customer:")}
    # All four spellings (Bayeriche / Bayersche / Bayerische x2) are one entity.
    assert customers == {
        "I_Customer:0010001002",
        "I_Customer:0010001003",
        "I_Customer:0010001019",
        "I_Customer:0010001020",
    }
    # The cluster is backed by traceable, confident assertions.
    links = [r for r in g.resolutions if r.node_a in entity and r.node_b in entity]
    assert links
    assert all(r.reason and r.confidence >= 0.85 for r in links)


def test_mueller_customer_and_address_resolve_to_one_entity() -> None:
    g = build_demo_graph()
    entity = g.entity_of(MUELLER)
    assert MUELLER_ADDR in entity  # customer master + address master, one entity


def test_distinct_logistics_firms_stay_separate() -> None:
    """Müller vs Nordwind both end in 'Logistik GmbH' but are different firms."""
    g = build_demo_graph()
    assert NORDWIND not in g.entity_of(MUELLER)


def test_resolution_is_reversible_on_the_demo_graph() -> None:
    g = build_demo_graph()
    entity = g.entity_of(MUELLER)
    assert MUELLER_ADDR in entity
    link = next(
        r for r in g.resolutions if {r.node_a, r.node_b} == {MUELLER, MUELLER_ADDR}
    )
    g.remove_resolution(link)
    # Withdrawing the assertion re-splits the cluster; raw nodes are untouched.
    assert MUELLER_ADDR not in g.entity_of(MUELLER)
    assert g.node(MUELLER).record.text  # record intact


def test_document_links_across_sources_to_its_entity() -> None:
    g = build_demo_graph()
    entity = g.entity_of(MUELLER)
    mentions = [m for m in g.mentions if m.node in entity]
    assert mentions  # the MSA chunk links to the Müller entity
    assert any(m.chunk.startswith("mueller_logistik_msa") for m in mentions)
    assert all(m.reason and m.confidence == 1.0 for m in mentions)


def test_lumiere_letter_is_a_known_unlinked_miss() -> None:
    """Honest limitation: the letter says 'Lumière Énergie' (legal form dropped),
    a form absent from the master data, so containment does not link it."""
    g = build_demo_graph()
    lumiere_chunks = {
        n.id for n in g.nodes if n.id.startswith("lumiere_energie_letter")
    }
    assert lumiere_chunks  # the letter was ingested
    assert not [m for m in g.mentions if m.chunk in lumiere_chunks]
