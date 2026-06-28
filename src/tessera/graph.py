"""An embedded, in-process knowledge graph with a non-destructive resolution layer.

Nodes wrap ingested :class:`~tessera.grounding.EvidenceRecord`s — their identity
and provenance are kept untouched. Structural edges capture known relationships
(e.g. a customer's address, a sales document's customer). Entity resolution is
**additive and reversible**: a :class:`Resolution` asserts that two
organization-name nodes refer to the same real entity, carrying a reason and a
confidence; resolved entities are the **connected components** of those
assertions, *derived* not stored — so removing an assertion re-splits the cluster
and never alters the underlying records (see ``docs/adr/0004-*``). Document
references are linked by additive :class:`Mention`s, again without editing data.

The graph is a plain in-process object model — no external graph database. SAP
HANA Cloud is the documented future persistence target (ADR 0004).
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.grounding import EvidenceRecord
from tessera.resolution import (
    DEFAULT_RESOLUTION_THRESHOLD,
    confirm_name_match,
    corpus_generic_tokens,
    normalize,
    similarity,
    strip_legal_suffix,
)


@dataclass(frozen=True)
class Node:
    """A graph node wrapping one ingested record. Provenance lives on the record.

    ``attributes`` is a small, vertical-neutral bag of structured facts a source
    chooses to expose for a node (e.g. a sales document's ``net_amount`` and
    ``currency``), so downstream engine code can use them without parsing text.
    """

    record: EvidenceRecord
    kind: str
    name: str | None = None  # the organization name, for name-bearing nodes
    attributes: tuple[tuple[str, str], ...] = ()

    @property
    def id(self) -> str:
        return self.record.id

    def attr(self, key: str) -> str | None:
        for k, value in self.attributes:
            if k == key:
                return value
        return None


@dataclass(frozen=True)
class Edge:
    """A known, deterministic structural relationship between two nodes."""

    src: str
    dst: str
    relation: str


@dataclass(frozen=True)
class Resolution:
    """Additive assertion that two org-name nodes refer to the same real entity.

    Non-destructive: it records *that* and *why* two nodes co-refer; it never
    changes the nodes. ``confidence`` is the similarity ``score`` used as a
    confidence proxy, not a calibrated probability.
    """

    node_a: str
    node_b: str
    score: float
    confidence: float
    reason: str


@dataclass(frozen=True)
class Mention:
    """Additive link from a document chunk to an org-name node it references."""

    chunk: str
    node: str
    confidence: float
    reason: str


class KnowledgeGraph:
    """Nodes + structural edges + the additive resolution/mention layers."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._resolutions: list[Resolution] = []
        self._mentions: list[Mention] = []

    # --- construction ---------------------------------------------------------
    def add_node(self, node: Node) -> None:
        self._nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    def add_resolution(self, resolution: Resolution) -> None:
        self._resolutions.append(resolution)

    def add_mention(self, mention: Mention) -> None:
        self._mentions.append(mention)

    def remove_resolution(self, resolution: Resolution) -> None:
        """Withdraw a same-entity assertion. Raw nodes/records are untouched, so
        the cluster simply re-splits — resolution is reversible by construction."""
        self._resolutions.remove(resolution)

    # --- access ---------------------------------------------------------------
    @property
    def nodes(self) -> tuple[Node, ...]:
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(self._edges)

    @property
    def resolutions(self) -> tuple[Resolution, ...]:
        return tuple(self._resolutions)

    @property
    def mentions(self) -> tuple[Mention, ...]:
        return tuple(self._mentions)

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def name_nodes(self) -> list[Node]:
        """Nodes that carry an organization name (the resolution candidates)."""
        return [node for node in self._nodes.values() if node.name]

    def sources_of(self, dst_ids: set[str], relation: str) -> list[str]:
        """Ids of nodes pointing into ``dst_ids`` via ``relation`` (e.g. the sales
        documents ``sold_to`` a set of customer nodes)."""
        return [
            e.src for e in self._edges if e.relation == relation and e.dst in dst_ids
        ]

    def mentions_of(self, node_ids: set[str]) -> list[Mention]:
        """Document mentions that point at any of ``node_ids``."""
        return [m for m in self._mentions if m.node in node_ids]

    # --- resolution layer -----------------------------------------------------
    def resolve_entities(self, threshold: float = DEFAULT_RESOLUTION_THRESHOLD) -> None:
        """Assert same-entity over name-bearing node pairs at/above ``threshold``.

        Deterministic and additive: it appends :class:`Resolution`s, leaving every
        node untouched. Each assertion records the matched normalized forms, the
        score, and the shared distinctive token, so it is inspectable.

        A character-similarity match is **gated** on a shared distinctive signal
        (:func:`~tessera.resolution.confirm_name_match`): a pair clears the
        threshold *and* must share a distinctive signal (a non-generic token, or a
        near-identical distinctive stem), so distinct firms whose high similarity
        comes only from a shared generic suffix ("… Logistik GmbH") no longer
        over-merge (spec 0070, ADR 0018). Genericness is corpus-derived
        (:func:`~tessera.resolution.corpus_generic_tokens`) so the demo graphs'
        typo/abbreviation variants are preserved while the generic-suffix cohort is
        split.

        The gate is a conjunctive tightening — it only ever *removes* a pairwise
        merge the bare ratio would have made, never adds one. The merges it removes
        are *usually* generic-suffix over-merges, but it can also drop a genuine
        match whose distinctive tokens are *both* typo'd at once (no shared token,
        stems too far apart); on the demo data those are rescued by transitivity
        through a cleaner co-referent, so the resolved clusters are byte-identical —
        but that is a property of this corpus, not a guarantee (ADR 0018).
        """
        candidates = self.name_nodes()
        generic = corpus_generic_tokens(
            [n.name for n in candidates if n.name is not None]
        )
        for i, left in enumerate(candidates):
            for right in candidates[i + 1 :]:
                assert left.name is not None and right.name is not None
                score = similarity(left.name, right.name)
                if score < threshold:
                    continue
                gate_reason = confirm_name_match(left.name, right.name, generic)
                if gate_reason is None:
                    continue  # no shared distinctive signal — a generic-suffix
                    # over-merge (or a rare double-typo the gate cannot bridge)
                reason = (
                    f"name match: {normalize(left.name)!r} ~ "
                    f"{normalize(right.name)!r} (similarity {score:.3f}; {gate_reason})"
                )
                self.add_resolution(
                    Resolution(
                        node_a=left.id,
                        node_b=right.id,
                        score=score,
                        confidence=score,
                        reason=reason,
                    )
                )

    def link_document_mentions(self) -> None:
        """Link document chunks to org-name nodes by normalized name containment.

        Deterministic and additive. Two needle forms are tried per name: the
        full normalized name (confidence 1.0) and, failing that, the name with
        its legal suffix stripped (confidence 0.9 — documents routinely drop
        the legal form, spec 0024); each mention's reason names the matched
        form, so the assertion stays inspectable.
        """
        documents = [n for n in self._nodes.values() if n.kind == "document"]
        for doc in documents:
            haystack = normalize(doc.record.text)
            for candidate in self.name_nodes():
                assert candidate.name is not None
                needle = normalize(candidate.name)
                if needle and needle in haystack:
                    self.add_mention(
                        Mention(
                            chunk=doc.id,
                            node=candidate.id,
                            confidence=1.0,
                            reason=f"document text contains {needle!r}",
                        )
                    )
                    continue
                stripped = strip_legal_suffix(candidate.name)
                if stripped and stripped in haystack:
                    self.add_mention(
                        Mention(
                            chunk=doc.id,
                            node=candidate.id,
                            confidence=0.9,
                            reason=(
                                f"document text contains {stripped!r} "
                                "(legal suffix stripped)"
                            ),
                        )
                    )

    # --- derived entities -----------------------------------------------------
    def clusters(self) -> list[frozenset[str]]:
        """Resolved entities: connected components over the resolution assertions.

        Derived on demand (not stored), so it always reflects the current
        assertions — withdraw one and the affected cluster re-splits.
        """
        parent = {node_id: node_id for node_id in self._nodes}

        def find(x: str) -> str:
            root = x
            while parent[root] != root:
                root = parent[root]
            while parent[x] != root:  # path compression
                parent[x], x = root, parent[x]
            return root

        for resolution in self._resolutions:
            a, b = resolution.node_a, resolution.node_b
            if a in parent and b in parent:
                parent[find(a)] = find(b)

        components: dict[str, set[str]] = {}
        for node_id in self._nodes:
            components.setdefault(find(node_id), set()).add(node_id)
        return [frozenset(members) for members in components.values()]

    def entity_of(self, node_id: str) -> frozenset[str]:
        """The resolved-entity cluster a node belongs to (itself if unresolved)."""
        for cluster in self.clusters():
            if node_id in cluster:
                return cluster
        return frozenset({node_id})
