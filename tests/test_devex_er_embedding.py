"""Embedding-assisted ER applied to the DevEx graph (spec 0063 / ADR 0016).

The mechanism (Unit 2) wired vertical-side into ``build_devex_graph`` behind the
``TESSERA_EMBEDDINGS`` selector, with the offline default unchanged. Proven here
with a seeded stub embedder (no network):

- **recall closed:** ``checkout-svc`` (difflib 0.846, undeclared) now resolves
  into ``checkout-service``'s entity, so the on-call surfaces;
- **precision held:** distinct services never over-merge;
- **reversible + faithful:** the embedding merge is an ordinary additive
  ``Resolution``, and the re-clustered graph still emits only supported claims;
- **none-path byte-identical:** with no resolver, ``checkout-svc`` stays the
  named miss it was, so CI's offline numbers do not move.

The real model's recall is the recorded online run (spec 0066), not this stub.
"""

from __future__ import annotations

from collections.abc import Sequence

from tessera.devex.knowledge import SemanticResolver, build_devex_graph
from tessera.devex.ownership import service_lookup
from tessera.er_semantic import (
    propose_semantic_resolutions,
    propose_semantic_resolutions_via_index,
)
from tessera.eval.metrics import is_supported
from tessera.graph import Resolution
from tessera.grounding import Answer
from tessera.platform.vectors import InMemoryVectorStore
from tessera.semantic import SemanticIndex

CHECKOUT_QUESTION = "Who is on call for checkout-service?"


class StubStemEmbeddings:
    """Keyword-axis stub over stems (no network); one axis per distinct service."""

    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0 if any(k in t.lower() for k in axis) else 0.0 for axis in self._axes]
            for t in texts
        ]


# One axis per service concept (notif matches both notif- and notifications-).
_AXES: list[tuple[str, ...]] = [
    ("checkout",),
    ("payments",),
    ("auth",),
    ("search",),
    ("notif",),
    ("inventory",),
]


def _stub_resolver() -> SemanticResolver:
    def resolve(named: list[tuple[str, str]]) -> list[Resolution]:
        return propose_semantic_resolutions(
            named, StubStemEmbeddings(_AXES), InMemoryVectorStore()
        )

    return resolve


def _cited_ids(answer: Answer) -> set[str]:
    return {rec.id for claim in answer.claims for rec in claim.support}


def _rendered(answer: Answer) -> str:
    return " ".join(claim.text for claim in answer.claims)


# --- the offline default is untouched ----------------------------------------


def test_none_path_keeps_checkout_svc_a_named_miss() -> None:
    graph = build_devex_graph()  # default: no resolver in CI (TESSERA_EMBEDDINGS unset)
    assert graph.entity_of("Owner:checkout-svc") == frozenset({"Owner:checkout-svc"})


def test_offline_ownership_answer_is_a_faithful_partial() -> None:
    graph = build_devex_graph()
    answer = service_lookup(CHECKOUT_QUESTION, graph)
    # The catalog row is surfaced (Storefront) but the on-call is NOT — it lives
    # under the unresolved checkout-svc node. This is the recorded offline miss.
    assert "Component:SVC-CHK" in _cited_ids(answer)
    assert "Owner:checkout-svc" not in _cited_ids(answer)
    assert "Jonas Lindqvist" not in _rendered(answer)
    # ...yet every emitted claim is supported — faithfulness holds at the miss.
    nodes = {n.id: n for n in graph.nodes}
    assert all(is_supported(c, nodes, graph, ()) for c in answer.claims)


# --- the embedding regime closes the recall miss, precisely -------------------


def test_embedding_resolves_checkout_svc_into_its_service() -> None:
    graph = build_devex_graph(semantic_resolver=_stub_resolver())
    assert "Owner:checkout-svc" in graph.entity_of("Component:SVC-CHK")


def test_embedding_does_not_over_merge_distinct_services() -> None:
    graph = build_devex_graph(semantic_resolver=_stub_resolver())
    checkout = graph.entity_of("Component:SVC-CHK")
    for other in ["SVC-PAY", "SVC-AUTH", "SVC-SRCH", "SVC-NOTIF", "SVC-INV"]:
        assert checkout.isdisjoint(graph.entity_of(f"Component:{other}")), other


def test_embedding_merge_is_reversible() -> None:
    graph = build_devex_graph(semantic_resolver=_stub_resolver())
    assert "Owner:checkout-svc" in graph.entity_of("Component:SVC-CHK")
    for resolution in [
        r
        for r in graph.resolutions
        if "embedding match" in r.reason
        and "Owner:checkout-svc" in (r.node_a, r.node_b)
    ]:
        graph.remove_resolution(resolution)
    assert graph.entity_of("Owner:checkout-svc") == frozenset({"Owner:checkout-svc"})


def test_embedding_resolution_is_auditable() -> None:
    graph = build_devex_graph(semantic_resolver=_stub_resolver())
    embedding_resolutions = [
        r for r in graph.resolutions if "embedding match" in r.reason
    ]
    assert embedding_resolutions  # the regime fired
    for resolution in embedding_resolutions:
        assert "cosine" in resolution.reason and "model stub" in resolution.reason
        assert 0.85 <= resolution.confidence <= 1.0


# --- the closed answer, and faithfulness under re-clustering ------------------


def test_online_ownership_answer_surfaces_the_oncall_and_stays_faithful() -> None:
    graph = build_devex_graph(semantic_resolver=_stub_resolver())
    answer = service_lookup(CHECKOUT_QUESTION, graph)
    assert answer.refusal is None
    assert {"Component:SVC-CHK", "Owner:checkout-svc"} <= _cited_ids(answer)
    assert "Jonas Lindqvist" in _rendered(answer) and "Storefront" in _rendered(answer)
    # Faithfulness holds with the re-clustered graph: every claim is supported.
    nodes = {n.id: n for n in graph.nodes}
    assert all(is_supported(c, nodes, graph, ()) for c in answer.claims)


# --- the HANA-native (via-index) path yields the same merge -------------------


def test_via_index_path_resolves_checkout_svc_offline() -> None:
    """The record-shaped index path (the HANA-native online analogue) reaches the
    same proposal as the provider+store path, proven offline with an in-memory
    index so the SQL-free contract is exercised key-free."""
    graph = build_devex_graph()
    named = [(n.id, n.name or "") for n in graph.name_nodes()]
    proposals = propose_semantic_resolutions_via_index(
        named,
        lambda: SemanticIndex(
            provider=StubStemEmbeddings(_AXES), store=InMemoryVectorStore()
        ),
        model_name="stub",
    )
    merged = {frozenset({r.node_a, r.node_b}) for r in proposals}
    assert frozenset({"Component:SVC-CHK", "Owner:checkout-svc"}) in merged
