"""Proof tests for Unit 4 on the real demo graph (spec 0014, constraint #4):
known variants resolve to one entity with traceable reasons + confidence, a known
non-match stays separate, the merge is reversible, and a document links across
sources to its entity.
"""

from __future__ import annotations

from tessera.business.knowledge import build_demo_graph
from tessera.graph import KnowledgeGraph
from tessera.sources.salt import ADDRESS_MATCH_FIELDS

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


_HANSEATIC = frozenset(
    {
        "I_Customer:0010000009",
        "I_Customer:0010000010",
        "I_AddrOrgNamePostalAddress:A0009",
        "I_AddrOrgNamePostalAddress:A0010",
    }
)

# The Milestone-10 same-name / SAME-address pair (spec 0079): two distinct "Havel
# Kontor GmbH" firms at one address, split only by their different VAT registration.
_HAVEL = frozenset(
    {
        "I_Customer:0010000011",
        "I_Customer:0010000012",
        "I_AddrOrgNamePostalAddress:A0011",
        "I_AddrOrgNamePostalAddress:A0012",
    }
)


def test_multifield_moves_only_the_intended_disambiguation_pairs() -> None:
    """The precision guarantee, **pinned not assumed** (spec 0074/0075/0079, ADR
    0019/0020). The default (registration-key) ER changes the resolved clusters in
    EXACTLY two places vs name-only — the two same-name disambiguation pairs (the
    Hanseatic different-address pair, spec 0075; the Havel same-address pair, spec
    0079) — and nowhere else. Every other cluster is byte-identical to name-only
    resolution; each pair splits from one over-merged cluster (name-only) into two
    same-named entities (the cure)."""
    multi = build_demo_graph()  # the registration-key default
    name_only = build_demo_graph(match_fields=())  # the Milestone-8 name-only state

    def others(graph: KnowledgeGraph) -> frozenset[frozenset[str]]:
        return frozenset(c for c in graph.clusters() if not (c & (_HANSEATIC | _HAVEL)))

    # Every cluster not touching a disambiguation pair is unchanged.
    assert others(multi) == others(name_only)
    # The intended changes: name-only over-merges each pair into one entity...
    for a, b in (
        ("I_Customer:0010000009", "I_Customer:0010000010"),
        ("I_Customer:0010000011", "I_Customer:0010000012"),
    ):
        assert name_only.entity_of(a) == name_only.entity_of(b)
        # ...the default ER splits each into two same-named entities (the cure).
        assert multi.entity_of(a) != multi.entity_of(b)


def test_multifield_bridges_the_double_typo_pair_directly() -> None:
    """The residual-3 improvement realized on the real demo graph: the Noridc/Nordic
    Timbre double-typo pair (which name-only leaves to transitivity) now merges
    DIRECTLY via an agreeing corroborating field — exactly one ``bridged by
    corroborating field`` assertion, naming the timber/timbre stems, without moving any
    cluster (ADR 0019). Under Milestone 10 the deciding field is the registration key:
    the two records are the same firm, so they share a VAT, and the key — leading
    ``CUSTOMER_MATCH_FIELDS`` — bridges them (spec 0078 / ADR 0020)."""
    multi = build_demo_graph()
    bridged = [
        r for r in multi.resolutions if "bridged by corroborating field" in r.reason
    ]
    assert len(bridged) == 1
    assert "timber" in bridged[0].reason and "timbre" in bridged[0].reason
    assert "vat_registration" in bridged[0].reason


def test_registration_key_splits_only_the_same_address_pair() -> None:
    """The Milestone-10 cluster-level close, **pinned not assumed** (spec 0078/0079,
    ADR 0020). The registration key changes the resolved clusters in EXACTLY one place
    vs the Milestone-9 address-only path — the same-name/SAME-address Havel Kontor pair,
    which the address gate over-merges (the address agrees) and the key splits (the two
    firms carry different VATs) — and nowhere else. This is both the non-regression
    guarantee (VAT-on-all moves no other cluster; a mis-assigned per-entity VAT would
    split a genuine merge and fail here) and the cluster-level demonstration of the
    key's contribution beyond the address."""
    key = build_demo_graph()  # the registration-key default
    address_only = build_demo_graph(match_fields=ADDRESS_MATCH_FIELDS)

    def others(graph: KnowledgeGraph) -> frozenset[frozenset[str]]:
        return frozenset(c for c in graph.clusters() if not (c & _HAVEL))

    # Every cluster away from the same-address pair is byte-identical.
    assert others(key) == others(address_only)
    # The one intended change: the address gate over-merges the same-address firms...
    a, b = "I_Customer:0010000011", "I_Customer:0010000012"
    assert address_only.entity_of(a) == address_only.entity_of(b)
    # ...the registration key splits them — the floor the address cannot reach.
    assert key.entity_of(a) != key.entity_of(b)
