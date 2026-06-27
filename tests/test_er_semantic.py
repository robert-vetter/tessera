"""Embedding-assisted ER (spec 0061 / ADR 0016): the stem-gated semantic
resolution regime resolves the opposite-direction tension in ONE rule —
abbreviation recall up (``checkout-svc``, declaration-free ``notif`` synonym),
generic-suffix precision held (``… Logistik GmbH`` distinct firms stay apart).

The stub embedder is a keyword-axis toy — it proves the *mechanism* and the
precision guard deterministically. The honest recall of non-identical synonym
stems by a real model is the recorded online run (spec 0066), not this test.
"""

from __future__ import annotations

from collections.abc import Sequence

from tessera.er_semantic import (
    DEFAULT_SEMANTIC_THRESHOLD,
    distinctive_stem,
    generic_tokens,
    propose_semantic_resolutions,
    tokenize,
)
from tessera.graph import KnowledgeGraph, Node, Resolution
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.platform.vectors import InMemoryVectorStore


class StubStemEmbeddings:
    """Deterministic keyword-axis embedder over *stems* — no network. Each axis
    is a concept; a stem's vector marks which concepts it mentions, so a synonym
    stem that shares no lexical token (``notif`` vs ``notifications``) still lands
    on the same axis, while distinct stems stay orthogonal."""

    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [
                1.0 if any(k in text.lower() for k in axis) else 0.0
                for axis in self._axes
            ]
            for text in texts
        ]


# One axis per distinctive concept. "notif" is a substring of both "notif" and
# "notifications", so those two synonym stems share an axis — the declaration-free
# bridge a real model would make. Granite/Pyrite/Müller/Nordwind are orthogonal.
_AXES = [
    ("checkout",),
    ("notif",),
    ("granite",),
    ("pyrite",),
    ("mueller", "muller"),
    ("nordwind",),
]

# Resolution candidates: two abbreviation pairs that SHOULD merge and a
# generic-suffix cohort that must NOT (distinct firms colliding on "Logistik GmbH").
_NAMED = [
    ("Component:CHK", "checkout-service"),
    ("Owner:checkout-svc", "checkout-svc"),
    ("Component:NOTIF", "notifications-service"),
    ("Owner:notif-svc", "notif-svc"),
    ("Customer:granite", "Granite Logistik GmbH"),
    ("Customer:pyrite", "Pyrite Logistik GmbH"),
    ("Customer:mueller", "Müller Logistik GmbH"),
    ("Customer:nordwind", "Nordwind Logistik GmbH"),
]


def _pairs(resolutions: list[Resolution]) -> set[frozenset[str]]:
    return {frozenset({r.node_a, r.node_b}) for r in resolutions}


# --- tokenization, generic derivation, stem extraction ------------------------


def test_tokenize_folds_and_splits() -> None:
    assert tokenize("checkout-service") == ["checkout", "service"]
    assert tokenize("Müller Logistik GmbH") == ["mueller", "logistik", "gmbh"]
    assert tokenize("notif-svc") == ["notif", "svc"]


def test_generic_tokens_combine_descriptors_legal_and_frequency() -> None:
    names = [name for _, name in _NAMED]
    generic = generic_tokens(names, min_df=3)
    # descriptors + legal forms are always generic
    assert "service" in generic and "svc" in generic and "gmbh" in generic
    # "logistik" is generic by corpus frequency (4 firms share it), unnamed
    assert "logistik" in generic
    # distinctive stems are kept (checkout appears in only 2 names; minerals in 1)
    assert "checkout" not in generic
    assert "granite" not in generic and "pyrite" not in generic


def test_distinctive_stem_strips_generics_to_the_identity_token() -> None:
    generic = generic_tokens([name for _, name in _NAMED], min_df=3)
    # the abbreviation pair collapses to the SAME stem (deterministic, no model)
    assert distinctive_stem("checkout-service", generic) == "checkout"
    assert distinctive_stem("checkout-svc", generic) == "checkout"
    # the synonym pair collapses to DIFFERENT stems (only a model bridges them)
    assert distinctive_stem("notifications-service", generic) == "notifications"
    assert distinctive_stem("notif-svc", generic) == "notif"
    # the generic-suffix cohort keeps distinct stems — this is what holds precision
    assert distinctive_stem("Granite Logistik GmbH", generic) == "granite"
    assert distinctive_stem("Pyrite Logistik GmbH", generic) == "pyrite"


# --- the proposer: recall up, precision held ----------------------------------


def test_proposer_merges_abbreviation_and_synonym_not_generic_suffix() -> None:
    proposals = propose_semantic_resolutions(
        _NAMED, StubStemEmbeddings(_AXES), InMemoryVectorStore()
    )
    assert _pairs(proposals) == {
        frozenset({"Component:CHK", "Owner:checkout-svc"}),  # stems coincide
        frozenset({"Component:NOTIF", "Owner:notif-svc"}),  # synonym stems bridged
    }
    # The generic-suffix cohort is NEVER proposed: distinct firms sharing only
    # "Logistik GmbH" reduce to distinct stems, so no embedding edge is asserted.
    for proposal in proposals:
        assert "Customer:granite" not in (proposal.node_a, proposal.node_b)
        assert "Customer:pyrite" not in (proposal.node_a, proposal.node_b)
        assert "Customer:mueller" not in (proposal.node_a, proposal.node_b)
        assert "Customer:nordwind" not in (proposal.node_a, proposal.node_b)


def test_proposals_are_auditable_resolutions() -> None:
    proposals = propose_semantic_resolutions(
        _NAMED, StubStemEmbeddings(_AXES), InMemoryVectorStore()
    )
    for proposal in proposals:
        assert proposal.score == proposal.confidence  # cosine used as the proxy
        assert 0.0 <= proposal.confidence <= 1.0
        assert "embedding match" in proposal.reason
        assert "cosine" in proposal.reason and "model stub" in proposal.reason


def test_proposer_is_deterministic_and_sorted() -> None:
    first = propose_semantic_resolutions(
        _NAMED, StubStemEmbeddings(_AXES), InMemoryVectorStore()
    )
    second = propose_semantic_resolutions(
        _NAMED, StubStemEmbeddings(_AXES), InMemoryVectorStore()
    )
    assert first == second
    assert first == sorted(first, key=lambda r: (r.node_a, r.node_b))


def test_threshold_blocks_orthogonal_stems() -> None:
    # With a threshold above 1.0 nothing can ever be proposed — the gate is real.
    proposals = propose_semantic_resolutions(
        _NAMED, StubStemEmbeddings(_AXES), InMemoryVectorStore(), threshold=1.0001
    )
    assert proposals == []
    # The default threshold is a documented cosine knob.
    assert DEFAULT_SEMANTIC_THRESHOLD == 0.85


def test_all_generic_name_is_never_proposed() -> None:
    # A name made only of generic tokens has an empty distinctive stem and is
    # never embedded or merged (it carries no identity signal).
    named = [("a", "Service GmbH"), ("b", "System AG")]
    assert (
        propose_semantic_resolutions(
            named, StubStemEmbeddings(_AXES), InMemoryVectorStore()
        )
        == []
    )


# --- the proposal is an ordinary additive, reversible graph assertion ---------


def _name_node(node_id: str, name: str) -> Node:
    return Node(
        record=EvidenceRecord(
            id=node_id,
            origin=Origin(
                source="er/test.csv",
                locator=Locator.table_row("t", 0),
                ingested_at="2026-06-27",
            ),
            text=name,
        ),
        kind="Customer",
        name=name,
    )


def test_added_proposal_merges_then_reverses() -> None:
    graph = KnowledgeGraph()
    graph.add_node(_name_node("Component:CHK", "checkout-service"))
    graph.add_node(_name_node("Owner:checkout-svc", "checkout-svc"))
    (proposal,) = propose_semantic_resolutions(
        [(n.id, n.name or "") for n in graph.name_nodes()],
        StubStemEmbeddings(_AXES),
        InMemoryVectorStore(),
    )
    graph.add_resolution(proposal)
    assert graph.entity_of("Component:CHK") == frozenset(
        {"Component:CHK", "Owner:checkout-svc"}
    )
    graph.remove_resolution(proposal)  # reversible by construction (ADR 0004)
    assert graph.entity_of("Component:CHK") == frozenset({"Component:CHK"})
    # raw records untouched throughout
    assert graph.node("Owner:checkout-svc").record.text == "checkout-svc"
