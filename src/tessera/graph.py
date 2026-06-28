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

from collections.abc import Sequence
from dataclasses import dataclass

from tessera.grounding import EvidenceRecord
from tessera.resolution import (
    DEFAULT_RESOLUTION_THRESHOLD,
    FieldSignal,
    compare_match_fields,
    confirm_name_match,
    corpus_generic_tokens,
    normalize,
    similarity,
    strip_legal_suffix,
)

# The address signal when no corroborating fields are compared (the none-path):
# resolution falls back to the pure name decision, byte-identical to Milestone 8.
_NO_FIELD_SIGNAL = FieldSignal("neutral", "")


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


def _merge_reason(
    name_a: str,
    name_b: str,
    score: float,
    gate_reason: str | None,
    signal: FieldSignal,
) -> str | None:
    """The two-way multi-field ER gate (ADR 0019).

    Given the name-pass result — ``gate_reason`` is the Milestone-8 stem gate's
    verdict (a string when it confirms a shared distinctive signal, ``None`` when it
    vetoes) — and the corroborating-field ``signal`` (address AGREE / CONTRADICT /
    NEUTRAL), return the assertion ``reason`` to record, or ``None`` to veto the merge:

    | name (stem gate) | address | outcome |
    |---|---|---|
    | confirmed | contradict | **veto** — same name, different address → distinct |
    | confirmed | agree / neutral | merge (reason notes any agreement) |
    | vetoed | agree | **merge** — address bridges a name-vetoed near-match |
    | vetoed | contradict / neutral | veto (as Milestone 8) |

    With ``signal`` NEUTRAL (the none-path, ``match_fields=()``) the returned reason
    is **byte-identical** to Milestone 8.
    """
    base = f"{normalize(name_a)!r} ~ {normalize(name_b)!r} (similarity {score:.3f}"
    if gate_reason is not None:
        # Name confirms — a contradicting address vetoes the over-merge.
        if signal.verdict == "contradict":
            return None
        address = f"; {signal.detail}" if signal.verdict == "agree" else ""
        return f"name match: {base}; {gate_reason}{address})"
    # Name vetoed by the stem gate — an agreeing address bridges the near-match.
    if signal.verdict == "agree":
        return f"name match stem-vetoed, bridged by address: {base}; {signal.detail})"
    return None


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
    def resolve_entities(
        self,
        threshold: float = DEFAULT_RESOLUTION_THRESHOLD,
        match_fields: Sequence[str] = (),
    ) -> None:
        """Assert same-entity over name-bearing node pairs at/above ``threshold``.

        Deterministic and additive: it appends :class:`Resolution`s, leaving every
        node untouched. Each assertion records the matched normalized forms, the
        score, and the shared distinctive token, so it is inspectable.

        A character-similarity match is first **gated** on a shared distinctive
        signal (:func:`~tessera.resolution.confirm_name_match`): a pair clears the
        threshold *and* must share a distinctive signal (a non-generic token, or a
        near-identical distinctive stem), so distinct firms whose high similarity
        comes only from a shared generic suffix ("… Logistik GmbH") no longer
        over-merge (spec 0070, ADR 0018).

        **Multi-field gate (spec 0073, ADR 0019).** When ``match_fields`` is given —
        an *ordered* tuple of corroborating attribute keys (e.g.
        ``("postal_code", "city_name")``) the source attaches to nodes — a second
        deterministic signal (the address) is folded into the name decision as a
        TWO-WAY gate (:func:`_merge_reason`): a contradicting address **vetoes** an
        over-merge of two same-named-but-distinct firms (residuals 1 & 2 of ADR
        0018), and an agreeing address **bridges** a name-vetoed near-match — a pair
        whose distinctive tokens are *both* typo'd (residual 3). The corroboration
        arm is reached only for pairs already at/above the name ``threshold``, so a
        low-name-similarity pair sharing an address (two firms in one building) can
        never false-merge.

        Default ``match_fields=()`` is **byte-identical** to Milestone 8 (the devex /
        github_actions none-path): no corroborating field is compared and the name
        decision stands alone. The model stays additive and reversible (ADR 0004):
        each confirmed pair is an ordinary :class:`Resolution`; clusters are derived
        connected components; ``remove_resolution`` re-splits.
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
                signal = (
                    compare_match_fields(
                        {field: left.attr(field) for field in match_fields},
                        {field: right.attr(field) for field in match_fields},
                        match_fields,
                    )
                    if match_fields
                    else _NO_FIELD_SIGNAL
                )
                reason = _merge_reason(
                    left.name, right.name, score, gate_reason, signal
                )
                if reason is None:
                    continue  # vetoed: generic-suffix over-merge, a contradicting
                    # address, or a double-typo with no bridging address
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
