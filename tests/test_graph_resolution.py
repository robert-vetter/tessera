"""Proof tests for Unit 4 on the real demo graph (spec 0014, constraint #4):
known variants resolve to one entity with traceable reasons + confidence, a known
non-match stays separate, the merge is reversible, and a document links across
sources to its entity.
"""

from __future__ import annotations

from tessera.business.knowledge import build_demo_graph
from tessera.graph import KnowledgeGraph

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


def test_lumiere_letter_links_via_suffix_stripped_mention() -> None:
    """Formerly the documented miss: the letter drops the legal form
    ('Lumière Énergie', master data says '... S.A.R.L.'). Spec 0024 closed it
    with diacritic folding + suffix-tolerant matching; the resulting mentions
    carry reduced confidence (0.9) and a reason naming the stripped form, so
    the weaker basis of the link stays inspectable."""
    g = build_demo_graph()
    lumiere_chunks = {
        n.id for n in g.nodes if n.id.startswith("lumiere_energie_letter")
    }
    assert lumiere_chunks  # the letter was ingested
    mentions = [m for m in g.mentions if m.chunk in lumiere_chunks]
    assert mentions
    assert all(m.confidence == 0.9 for m in mentions)
    assert all("legal suffix stripped" in m.reason for m in mentions)


def _cluster_signature(graph: KnowledgeGraph) -> frozenset[frozenset[str]]:
    """A canonical, order-independent signature of the resolved clusters."""
    return frozenset(graph.clusters())


def test_multifield_resolution_does_not_move_any_existing_cluster() -> None:
    """The Milestone-9 no-regression guarantee, **pinned not assumed** (spec 0074 /
    ADR 0019). Multi-field ER must be inert on the existing demo data: every genuine
    merge already agrees on postal, and no character-identical distinct firm exists
    yet, so the resolved clusters are byte-identical to name-only resolution (the
    Milestone-8 state)."""
    multi = build_demo_graph()  # match_fields = postal + city (the default)
    name_only = build_demo_graph(match_fields=())  # the Milestone-8 name-only state
    assert _cluster_signature(multi) == _cluster_signature(name_only)


def test_multifield_bridges_the_double_typo_pair_directly() -> None:
    """The residual-3 improvement realized on the real demo graph: the Noridc/Nordic
    Timbre double-typo pair (which name-only leaves to transitivity) now merges
    DIRECTLY via an agreeing address — exactly one extra assertion, same clusters.
    This strengthens the assertion set without moving any cluster (ADR 0019)."""
    multi = build_demo_graph()
    bridged = [r for r in multi.resolutions if "bridged by address" in r.reason]
    assert len(bridged) == 1
    assert "timber" in bridged[0].reason and "timbre" in bridged[0].reason
    # Exactly one MORE assertion than name-only, and the clusters are unchanged.
    name_only = build_demo_graph(match_fields=())
    assert len(multi.resolutions) == len(name_only.resolutions) + 1
