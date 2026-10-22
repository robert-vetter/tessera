"""Dict round-trips for the trust-bundle chain — the reconstruction layer.

Spec 0132 (ROADMAP3 Milestone 20, unit 1). ``tessera verify`` (unit 0134) must
rebuild, from a JSON file alone, exactly the objects the live verifier
consumes. This module is that inverse: ``from_dict`` functions for every
boundary object that already serializes itself (``GroundedResult``,
``RenderedPayload``, ``ActionProposal``, ``ExecutionReceipt`` and their
parts), and both directions for the core objects that had no dict form
(``EvidenceRecord``, ``Claim``, ``Node``, the ``KnowledgeGraph``, the
``KnowledgeBase``).

Three properties the fidelity tests pin:

- **Lossless.** ``to_dict → from_dict → to_dict`` is byte-identical under
  canonical dumps, and a rebuilt graph is tuple-exact (nodes, edges,
  resolutions, mentions) — the losslessness standard ``platform/kg.py`` set.
- **Order-preserving.** Serialization walks the graph's own insertion order
  and reconstruction replays it through the ordinary ``add_*`` methods; this
  layer never reorders data (canonical ordering for hashing is unit 0133's
  concern, applied to emitted bytes).
- **Strict.** Malformed input raises :class:`ValueError` naming the offending
  key; unknown extra keys are ignored (forward compatibility). Derived fields
  (``all_verified``, ``all_grounded``, ``locator.render``) are recomputed by
  the objects themselves and never read back.

A strict consumer of existing seams: nothing in the frozen core or the agent
layer changes. Pure stdlib — the leak-guard (``tests/test_agent.py``) holds.
"""

from __future__ import annotations

from tessera.agent.actions import ActionField, ActionProposal
from tessera.agent.execution import ExecutionReceipt
from tessera.agent.grounded import GroundedClaim, GroundedEvidence, GroundedResult
from tessera.agent.payloads import PayloadSlot, RenderedPayload
from tessera.graph import Edge, KnowledgeGraph, Mention, Node, Resolution
from tessera.grounding import Claim, EvidenceRecord, KnowledgeBase, Locator, Origin

# --- strict, typed extraction ---------------------------------------------------
#
# Every reader names the key it failed on, so a malformed bundle fails loudly at
# the exact field — unit 0134 wraps these into the verify CLI's clean error path.


def _dict(value: object, key: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"expected an object at {key!r}, got {type(value).__name__}")
    return value


def _list(value: object, key: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"expected a list at {key!r}, got {type(value).__name__}")
    return value


def _get(mapping: dict[str, object], key: str) -> object:
    if key not in mapping:
        raise ValueError(f"missing key {key!r}")
    return mapping[key]


def _str(mapping: dict[str, object], key: str) -> str:
    value = _get(mapping, key)
    if not isinstance(value, str):
        raise ValueError(f"expected a string at {key!r}, got {type(value).__name__}")
    return value


def _opt_str(mapping: dict[str, object], key: str) -> str | None:
    value = _get(mapping, key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            f"expected a string or null at {key!r}, got {type(value).__name__}"
        )
    return value


def _bool(mapping: dict[str, object], key: str) -> bool:
    value = _get(mapping, key)
    if not isinstance(value, bool):
        raise ValueError(f"expected a boolean at {key!r}, got {type(value).__name__}")
    return value


def _float(mapping: dict[str, object], key: str) -> float:
    value = _get(mapping, key)
    # bool is an int subclass; a boolean here would be a shape error, not a number.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected a number at {key!r}, got {type(value).__name__}")
    return float(value)


def _pairs(value: object, key: str) -> tuple[tuple[str, str], ...]:
    """A list of two-string pairs (locator parts, node attributes)."""
    out: list[tuple[str, str]] = []
    for i, item in enumerate(_list(value, key)):
        pair = _list(item, f"{key}[{i}]")
        if len(pair) != 2 or not all(isinstance(p, str) for p in pair):
            raise ValueError(f"expected a [str, str] pair at {key}[{i}]")
        first, second = pair
        assert isinstance(first, str) and isinstance(second, str)
        out.append((first, second))
    return tuple(out)


# --- core: locator / origin / record / claim ------------------------------------


def locator_to_dict(locator: Locator) -> dict[str, object]:
    return {
        "kind": locator.kind,
        "parts": [[label, value] for label, value in locator.parts],
    }


def locator_from_dict(data: dict[str, object]) -> Locator:
    return Locator(kind=_str(data, "kind"), parts=_pairs(_get(data, "parts"), "parts"))


def origin_to_dict(origin: Origin) -> dict[str, object]:
    return {
        "source": origin.source,
        "locator": locator_to_dict(origin.locator),
        "ingested_at": origin.ingested_at,
    }


def origin_from_dict(data: dict[str, object]) -> Origin:
    return Origin(
        source=_str(data, "source"),
        locator=locator_from_dict(_dict(_get(data, "locator"), "locator")),
        ingested_at=_str(data, "ingested_at"),
    )


def record_to_dict(record: EvidenceRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "origin": origin_to_dict(record.origin),
        "text": record.text,
    }


def record_from_dict(data: dict[str, object]) -> EvidenceRecord:
    return EvidenceRecord(
        id=_str(data, "id"),
        origin=origin_from_dict(_dict(_get(data, "origin"), "origin")),
        text=_str(data, "text"),
    )


# A bare ``Claim`` never crosses into a bundle on its own — claims travel as
# ``GroundedClaim`` (verdict + provenance) and are rebuilt for re-verification
# by :func:`claim_from_grounded` below — so no ``Claim`` dict pair is defined.


# --- core: graph and knowledge base ----------------------------------------------


def node_to_dict(node: Node) -> dict[str, object]:
    return {
        "record": record_to_dict(node.record),
        "kind": node.kind,
        "name": node.name,
        "attributes": [[key, value] for key, value in node.attributes],
    }


def node_from_dict(data: dict[str, object]) -> Node:
    return Node(
        record=record_from_dict(_dict(_get(data, "record"), "record")),
        kind=_str(data, "kind"),
        name=_opt_str(data, "name"),
        attributes=_pairs(_get(data, "attributes"), "attributes"),
    )


def edge_to_dict(edge: Edge) -> dict[str, object]:
    return {"src": edge.src, "dst": edge.dst, "relation": edge.relation}


def edge_from_dict(data: dict[str, object]) -> Edge:
    return Edge(
        src=_str(data, "src"), dst=_str(data, "dst"), relation=_str(data, "relation")
    )


def resolution_to_dict(resolution: Resolution) -> dict[str, object]:
    return {
        "node_a": resolution.node_a,
        "node_b": resolution.node_b,
        "score": resolution.score,
        "confidence": resolution.confidence,
        "reason": resolution.reason,
    }


def resolution_from_dict(data: dict[str, object]) -> Resolution:
    return Resolution(
        node_a=_str(data, "node_a"),
        node_b=_str(data, "node_b"),
        score=_float(data, "score"),
        confidence=_float(data, "confidence"),
        reason=_str(data, "reason"),
    )


def mention_to_dict(mention: Mention) -> dict[str, object]:
    return {
        "chunk": mention.chunk,
        "node": mention.node,
        "confidence": mention.confidence,
        "reason": mention.reason,
    }


def mention_from_dict(data: dict[str, object]) -> Mention:
    return Mention(
        chunk=_str(data, "chunk"),
        node=_str(data, "node"),
        confidence=_float(data, "confidence"),
        reason=_str(data, "reason"),
    )


def graph_to_dict(graph: KnowledgeGraph) -> dict[str, object]:
    """The full graph snapshot, in the graph's own insertion order."""
    return {
        "nodes": [node_to_dict(node) for node in graph.nodes],
        "edges": [edge_to_dict(edge) for edge in graph.edges],
        "resolutions": [resolution_to_dict(r) for r in graph.resolutions],
        "mentions": [mention_to_dict(m) for m in graph.mentions],
    }


def graph_from_dict(data: dict[str, object]) -> KnowledgeGraph:
    """Rebuild a graph by replaying the snapshot through the ordinary ``add_*``
    methods, preserving order — tuple-exact against the original."""
    graph = KnowledgeGraph()
    for i, item in enumerate(_list(_get(data, "nodes"), "nodes")):
        graph.add_node(node_from_dict(_dict(item, f"nodes[{i}]")))
    for i, item in enumerate(_list(_get(data, "edges"), "edges")):
        graph.add_edge(edge_from_dict(_dict(item, f"edges[{i}]")))
    for i, item in enumerate(_list(_get(data, "resolutions"), "resolutions")):
        graph.add_resolution(resolution_from_dict(_dict(item, f"resolutions[{i}]")))
    for i, item in enumerate(_list(_get(data, "mentions"), "mentions")):
        graph.add_mention(mention_from_dict(_dict(item, f"mentions[{i}]")))
    return graph


def kb_to_dict(kb: KnowledgeBase) -> dict[str, object]:
    return {"records": [record_to_dict(record) for record in kb.records]}


def kb_from_dict(data: dict[str, object]) -> KnowledgeBase:
    return KnowledgeBase(
        records=tuple(
            record_from_dict(_dict(item, f"records[{i}]"))
            for i, item in enumerate(_list(_get(data, "records"), "records"))
        )
    )


# --- boundary: the grounded answer ------------------------------------------------


def grounded_evidence_from_dict(data: dict[str, object]) -> GroundedEvidence:
    locator = _dict(_get(data, "locator"), "locator")
    return GroundedEvidence(
        id=_str(data, "id"),
        source=_str(data, "source"),
        locator_kind=_str(locator, "kind"),
        locator_parts=_pairs(_get(locator, "parts"), "locator.parts"),
        ingested_at=_str(data, "ingested_at"),
        text=_str(data, "text"),
    )


def grounded_claim_from_dict(data: dict[str, object]) -> GroundedClaim:
    return GroundedClaim(
        text=_str(data, "text"),
        verified=_bool(data, "verified"),
        support=tuple(
            grounded_evidence_from_dict(_dict(item, f"support[{i}]"))
            for i, item in enumerate(_list(_get(data, "support"), "support"))
        ),
    )


def grounded_result_from_dict(data: dict[str, object]) -> GroundedResult:
    route = _dict(_get(data, "route"), "route")
    return GroundedResult(
        domain=_str(data, "domain"),
        question=_str(data, "question"),
        route_kind=_str(route, "kind"),
        route_reason=_str(route, "reason"),
        grounded=_bool(data, "grounded"),
        refused=_bool(data, "refused"),
        refusal=_opt_str(data, "refusal"),
        claims=tuple(
            grounded_claim_from_dict(_dict(item, f"claims[{i}]"))
            for i, item in enumerate(_list(_get(data, "claims"), "claims"))
        ),
    )


# --- boundary: the action chain ----------------------------------------------------


def payload_slot_from_dict(data: dict[str, object]) -> PayloadSlot:
    return PayloadSlot(
        part=_str(data, "part"),
        role=_str(data, "role"),
        label=_str(data, "label"),
        value=_str(data, "value"),
        verified=_bool(data, "verified"),
        support=tuple(
            grounded_evidence_from_dict(_dict(item, f"support[{i}]"))
            for i, item in enumerate(_list(_get(data, "support"), "support"))
        ),
    )


def rendered_payload_from_dict(data: dict[str, object]) -> RenderedPayload:
    route = _dict(_get(data, "route"), "route")
    request = _dict(_get(data, "request"), "request")
    return RenderedPayload(
        kind=_str(data, "kind"),
        domain=_str(data, "domain"),
        question=_str(data, "question"),
        target=_str(data, "target"),
        method=_str(request, "method"),
        path=_str(request, "path"),
        body=_dict(_get(request, "body"), "request.body"),
        slots=tuple(
            payload_slot_from_dict(_dict(item, f"slots[{i}]"))
            for i, item in enumerate(_list(_get(data, "slots"), "slots"))
        ),
        rendered=_bool(data, "rendered"),
        withheld_reason=_opt_str(data, "withheld_reason"),
        route_kind=_str(route, "kind"),
        route_reason=_str(route, "reason"),
        sent=_bool(data, "sent"),
        requires_approval=_bool(data, "requires_approval"),
    )


def action_field_from_dict(data: dict[str, object]) -> ActionField:
    return ActionField(
        name=_str(data, "name"),
        value=_str(data, "value"),
        verified=_bool(data, "verified"),
        support=tuple(
            grounded_evidence_from_dict(_dict(item, f"support[{i}]"))
            for i, item in enumerate(_list(_get(data, "support"), "support"))
        ),
    )


def action_proposal_from_dict(data: dict[str, object]) -> ActionProposal:
    route = _dict(_get(data, "route"), "route")
    return ActionProposal(
        kind=_str(data, "kind"),
        domain=_str(data, "domain"),
        question=_str(data, "question"),
        route_kind=_str(route, "kind"),
        route_reason=_str(route, "reason"),
        grounded=_bool(data, "grounded"),
        refused=_bool(data, "refused"),
        refusal=_opt_str(data, "refusal"),
        fields=tuple(
            action_field_from_dict(_dict(item, f"fields[{i}]"))
            for i, item in enumerate(_list(_get(data, "fields"), "fields"))
        ),
        requires_approval=_bool(data, "requires_approval"),
        executed=_bool(data, "executed"),
    )


def execution_receipt_from_dict(data: dict[str, object]) -> ExecutionReceipt:
    route = _dict(_get(data, "route"), "route")
    request = _dict(_get(data, "request"), "request")
    return ExecutionReceipt(
        kind=_str(data, "kind"),
        domain=_str(data, "domain"),
        question=_str(data, "question"),
        target=_str(data, "target"),
        method=_str(request, "method"),
        path=_str(request, "path"),
        body=_dict(_get(request, "body"), "request.body"),
        slots=tuple(
            payload_slot_from_dict(_dict(item, f"slots[{i}]"))
            for i, item in enumerate(_list(_get(data, "slots"), "slots"))
        ),
        actuator=_str(data, "actuator"),
        payload_grounded=_bool(data, "payload_grounded"),
        executed=_bool(data, "executed"),
        simulated=_bool(data, "simulated"),
        sent=_bool(data, "sent"),
        withheld=_bool(data, "withheld"),
        withheld_reason=_opt_str(data, "withheld_reason"),
        outcome=_str(data, "outcome"),
        result=_dict(_get(data, "result"), "result"),
        idempotency_key=_opt_str(data, "idempotency_key"),
        approved=_bool(data, "approved"),
        requires_approval=_bool(data, "requires_approval"),
        route_kind=_str(route, "kind"),
        route_reason=_str(route, "reason"),
    )


# --- the re-verification bridge -----------------------------------------------------
#
# The point of the whole layer: rebuild the exact inputs the eval verifier
# consumes from the serialized boundary form, so unit 0134 can re-run
# ``is_supported`` over a bundle's claims against its packaged graph.


def record_from_evidence(evidence: GroundedEvidence) -> EvidenceRecord:
    """The :class:`EvidenceRecord` a serialized :class:`GroundedEvidence` came
    from — the boundary projection (``agent.grounded._evidence``) inverted."""
    return EvidenceRecord(
        id=evidence.id,
        origin=Origin(
            source=evidence.source,
            locator=Locator(kind=evidence.locator_kind, parts=evidence.locator_parts),
            ingested_at=evidence.ingested_at,
        ),
        text=evidence.text,
    )


def claim_from_grounded(claim: GroundedClaim) -> Claim:
    """The core :class:`Claim` behind a serialized :class:`GroundedClaim` — the
    input ``is_supported`` consumes. Provenance-mandatory by construction:
    a boundary claim always carries support, so the ``Claim`` invariant
    (non-empty support) survives reconstruction."""
    return Claim(
        text=claim.text,
        support=tuple(record_from_evidence(e) for e in claim.support),
    )
