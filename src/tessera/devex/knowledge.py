"""Assemble the DevEx knowledge base and graph from the ingested corpus.

The DevEx counterpart to :mod:`tessera.business.knowledge`, built with the **same,
unchanged** engine machinery (spec 0028): nodes wrap ingested records,
foreign keys become structural edges, then the additive resolution layer
asserts which catalog/on-call names co-refer and the mention pass links log
and diff chunks to the services they name. Log chunks and diff hunks carry
the engine's ``document`` kind — "document" means *unstructured chunk node*
(ADR 0008); what file family a chunk came from stays visible in its origin.

The resolution outcomes on this corpus are measured, not assumed: the
catalog↔on-call variants for payments/auth/search/inventory merge at the
0.85 threshold. Phase 3 left two abbreviations unresolved as *named* recall
misses (spec 0026); the eval measured ``notif-svc`` (similarity 0.429) as
the 0.917 coverage gap, and the catalog now closes it with a **declared
alias** asserted here as an ordinary, reversible :class:`Resolution`
(spec 0036 / ADR 0010). ``checkout-svc`` (0.846) stays undeclared and
unresolved — aliases only fix what someone declares.
"""

from __future__ import annotations

from collections.abc import Callable

from tessera.graph import Edge, KnowledgeGraph, Node, Resolution
from tessera.grounding import KnowledgeBase
from tessera.resolution import DEFAULT_RESOLUTION_THRESHOLD, normalize
from tessera.sources.devex import DevExSource
from tessera.sources.github_actions import GitHubActionsSource

# The kinds that arrive as unstructured chunks (and so participate in the
# engine's document-mention linking).
_CHUNK_LOCATOR_KINDS = frozenset({"log-span", "diff-hunk"})

DEMO_QUESTION = "Why did run R-1042 fail?"

# A resolver proposes additive same-entity Resolutions from the name-bearing
# nodes; the embedding-assisted one (spec 0063 / ADR 0016) is built from the
# TESSERA_EMBEDDINGS selector and is None in the default offline mode.
SemanticResolver = Callable[[list[tuple[str, str]]], list[Resolution]]

# The HANA table for ER stem vectors — deliberately separate from the
# retrieval doc-vector table, so ER linking and document retrieval never share
# a vector space.
_ER_VECTOR_TABLE = "TESSERA_ER_VECTORS"


def build_devex_kb() -> KnowledgeBase:
    """All DevEx records as one retrievable knowledge base."""
    return KnowledgeBase(records=tuple(DevExSource().ingest()))


def build_devex_graph(
    threshold: float = DEFAULT_RESOLUTION_THRESHOLD,
    *,
    semantic_resolver: SemanticResolver | None = None,
) -> KnowledgeGraph:
    """One graph over all eight DevEx source shapes, resolved and linked.

    Three additive resolution regimes run in order, each leaving the nodes
    untouched (ADR 0004/0010/0016): deterministic ``difflib`` similarity, then
    declared catalog aliases, then — only when embeddings are configured — the
    embedding-assisted regime (spec 0063), which bridges abbreviation/synonym
    variants ``difflib`` misses (e.g. ``checkout-svc``). ``semantic_resolver`` is
    injected for offline tests; otherwise it is built from the
    ``TESSERA_EMBEDDINGS`` selector and is ``None`` in the default offline mode,
    so the graph is byte-identical to before and ``checkout-svc`` stays a named
    miss.
    """
    source = DevExSource()
    org_names = source.org_names()
    node_attrs = source.node_attributes()

    graph = KnowledgeGraph()
    for record in source.ingest():
        if record.origin.locator.kind in _CHUNK_LOCATOR_KINDS:
            kind = "document"
        else:
            kind = record.id.split(":", 1)[0]  # the table name
        graph.add_node(
            Node(
                record=record,
                kind=kind,
                name=org_names.get(record.id),
                attributes=node_attrs.get(record.id, ()),
            )
        )

    for src, dst, relation in source.structural_edges():
        graph.add_edge(Edge(src=src, dst=dst, relation=relation))

    graph.resolve_entities(threshold)
    _assert_declared_aliases(graph, source.declared_aliases())
    _apply_embedding_resolution(graph, semantic_resolver)
    graph.link_document_mentions()
    return graph


def _apply_embedding_resolution(
    graph: KnowledgeGraph, semantic_resolver: SemanticResolver | None
) -> None:
    """Add the embedding-assisted regime's proposals, if one is configured.

    Vertical-side by the ADR 0010 precedent (the engine stays embedding-free);
    each proposal is an ordinary additive, reversible ``Resolution``.
    """
    resolver = (
        semantic_resolver
        if semantic_resolver is not None
        else _devex_semantic_resolver_from_env()
    )
    if resolver is None:
        return
    named = [(node.id, node.name) for node in graph.name_nodes() if node.name]
    for proposal in resolver(named):
        graph.add_resolution(proposal)


def _devex_semantic_resolver_from_env() -> SemanticResolver | None:
    """Build the embedding-assisted resolver from ``TESSERA_EMBEDDINGS``.

    ``none`` (the default) → ``None``: no embedding ER, the offline path is
    untouched. ``hana`` → the HANA-native in-database path (the recorded online
    path, spec 0066). ``genai-hub`` → a provider+store path. All embedding imports
    are lazy, so the default clone-and-run import graph carries no cloud code.
    """
    from tessera.platform.config import EMBEDDINGS_HANA, EMBEDDINGS_NONE, load_config

    cfg = load_config()
    if cfg.embeddings == EMBEDDINGS_NONE:
        return None

    from tessera.er_semantic import (
        propose_semantic_resolutions,
        propose_semantic_resolutions_via_index,
    )

    if cfg.embeddings == EMBEDDINGS_HANA:
        from tessera.semantic import HanaSemanticIndex

        def resolve_hana(named: list[tuple[str, str]]) -> list[Resolution]:
            return propose_semantic_resolutions_via_index(
                named,
                lambda: HanaSemanticIndex(config=cfg, table=_ER_VECTOR_TABLE),
                model_name=cfg.hana_embedding_model,
            )

        return resolve_hana

    from tessera.platform.providers import embedding_provider_from_env
    from tessera.platform.vectors import (
        HanaVectorStore,
        InMemoryVectorStore,
        VectorStore,
    )

    provider = embedding_provider_from_env(cfg)
    if provider is None:
        return None
    store: VectorStore = (
        HanaVectorStore(config=cfg, table=_ER_VECTOR_TABLE)
        if cfg.hana_host
        else InMemoryVectorStore()
    )

    def resolve_provider(named: list[tuple[str, str]]) -> list[Resolution]:
        return propose_semantic_resolutions(named, provider, store)

    return resolve_provider


def build_github_actions_kb() -> KnowledgeBase:
    """All real GitHub Actions snapshot records as one retrievable base."""
    return KnowledgeBase(records=tuple(GitHubActionsSource().ingest()))


def build_github_actions_graph() -> KnowledgeGraph:
    """A **separate** graph over the real GitHub Actions snapshot (spec 0045).

    Deliberately its own graph, not unioned into the synthetic DevEx graph: the
    synthetic battery's numbers stay byte-identical, and the real-data miss the
    next unit measures (spec 0046) is isolated in its own battery. The same
    engine machinery — run rows as structured nodes, failed-step log chunks as
    ``document`` nodes, ``log_of`` edges — with no resolution layer (the
    snapshot carries no service catalog to resolve against).
    """
    source = GitHubActionsSource()
    node_attrs = source.node_attributes()

    graph = KnowledgeGraph()
    for record in source.ingest():
        if record.origin.locator.kind in _CHUNK_LOCATOR_KINDS:
            kind = "document"
        else:
            kind = record.id.split(":", 1)[0]  # "Run"
        graph.add_node(
            Node(
                record=record,
                kind=kind,
                attributes=node_attrs.get(record.id, ()),
            )
        )

    for src, dst, relation in source.structural_edges():
        graph.add_edge(Edge(src=src, dst=dst, relation=relation))
    return graph


def _assert_declared_aliases(
    graph: KnowledgeGraph, declared: dict[str, tuple[str, ...]]
) -> None:
    """Assert same-entity for every name-bearing node a catalog alias names.

    Deliberately vertical-side (the engine stays untouched until a second
    vertical needs alias data — spec 0036) and deliberately *exact*: an alias
    matches by normalized equality, never similarity, so a declaration cannot
    transitively bridge two distinct services. Each assertion is an ordinary
    additive :class:`~tessera.graph.Resolution` — confidence 1.0 because it is
    declared catalog data, with a reason naming the declaration — so it stays
    inspectable and reversible like every other merge decision.
    """
    for component_id, aliases in sorted(declared.items()):
        for alias in aliases:
            needle = normalize(alias)
            for node in graph.name_nodes():
                assert node.name is not None
                if node.id != component_id and normalize(node.name) == needle:
                    graph.add_resolution(
                        Resolution(
                            node_a=component_id,
                            node_b=node.id,
                            score=1.0,
                            confidence=1.0,
                            reason=(
                                f"declared catalog alias: {alias!r} is listed "
                                f"for {component_id} in components.csv"
                            ),
                        )
                    )
