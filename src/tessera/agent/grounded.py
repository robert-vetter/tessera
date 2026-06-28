"""The grounded-tool layer's substance: a domain registry and read-only tools.

This is the single source of truth for *what an agent can ask about* (the domains)
and *how a grounded answer crosses the boundary* (the serializable, verifier-checked
result). It reuses each vertical's deterministic router and the eval's structural
verifier (``is_supported``) — adding a new *consumer* of the engine, not a new answer
path. Pure-stdlib and offline: it uses each domain's lexical path, so importing this
module pulls no embedding / LLM / ``hdbcli`` / ``mcp`` import toward the verifier
(the leak-guard, extended in ``tests/test_agent.py``, holds).

Read-only by design (ADR 0022): the tools *return* evidence; nothing here writes,
executes, or proposes a side-effecting action.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tessera.eval.metrics import ClaimShape, is_supported
from tessera.graph import KnowledgeGraph, Mention, Node, Resolution
from tessera.grounding import REFUSAL_MESSAGE, Answer, EvidenceRecord, KnowledgeBase
from tessera.routing import Route

RouteFn = Callable[[str, KnowledgeGraph, KnowledgeBase], "tuple[Route, Answer]"]


# --- the domain registry ------------------------------------------------------


@dataclass(frozen=True)
class GroundedDomain:
    """A domain an agent can ask about: its engines, router, and claim grammars.

    ``build`` constructs the (graph, kb) once; ``route`` is the vertical's
    deterministic router; ``claim_shapes`` are its declared verifier grammars
    (ADR 0011), used to live-verify every emitted claim at the boundary.
    """

    name: str
    description: str
    build: Callable[[], tuple[KnowledgeGraph, KnowledgeBase]]
    route: RouteFn
    claim_shapes: tuple[ClaimShape, ...]


def _business_domain() -> GroundedDomain:
    from tessera.business.claims import BUSINESS_CLAIM_SHAPES
    from tessera.business.knowledge import build_demo_graph, build_demo_kb
    from tessera.business.routing import route

    return GroundedDomain(
        name="business",
        description=(
            "Business Data Copilot: customers, sales orders, and contract "
            "documents from the synthetic SALT master data plus authored "
            "agreements. Answers lookups, cross-source summaries, multi-entity "
            "comparisons, and surfaces conflicts; refuses ambiguous entities."
        ),
        build=lambda: (build_demo_graph(), build_demo_kb()),
        route=route,
        claim_shapes=BUSINESS_CLAIM_SHAPES,
    )


def _devex_domain() -> GroundedDomain:
    from tessera.devex.knowledge import build_devex_graph, build_devex_kb
    from tessera.devex.routing import route

    return GroundedDomain(
        name="devex",
        description=(
            "DevEx Copilot: CI/CD runs and logs, PR diffs, tickets, and service "
            "ownership. Answers root-cause questions for failed runs (grounded in "
            "log lines, linked to prior incidents), PR change-summaries tied to "
            "tickets, and ownership lookups; refuses on insufficient evidence."
        ),
        build=lambda: (build_devex_graph(), build_devex_kb()),
        route=route,
        claim_shapes=(),
    )


def _github_actions_domain() -> GroundedDomain:
    # GitHub Actions data *is* CI data, so the devex router applies unchanged over
    # the committed real-snapshot graph (the eval's github_actions battery does the
    # same, ADR 0014). The lexical path is used here (offline, deterministic).
    from tessera.devex.knowledge import (
        build_github_actions_graph,
        build_github_actions_kb,
    )
    from tessera.devex.routing import route

    return GroundedDomain(
        name="github_actions",
        description=(
            "The real GitHub Actions connector: this repository's own committed "
            "CI run history and runner logs. Answers root-cause questions for "
            "failed runs grounded in the actual log lines; refuses otherwise."
        ),
        build=lambda: (build_github_actions_graph(), build_github_actions_kb()),
        route=route,
        claim_shapes=(),
    )


_DOMAIN_FACTORIES: dict[str, Callable[[], GroundedDomain]] = {
    "business": _business_domain,
    "devex": _devex_domain,
    "github_actions": _github_actions_domain,
}

_domain_cache: dict[str, GroundedDomain] = {}
_engine_cache: dict[str, tuple[KnowledgeGraph, KnowledgeBase]] = {}


def available_domains() -> tuple[str, ...]:
    """The domains an agent can ground a question in."""
    return tuple(_DOMAIN_FACTORIES)


def domain(name: str) -> GroundedDomain:
    """The :class:`GroundedDomain` for ``name`` (built once, cached)."""
    if name not in _DOMAIN_FACTORIES:
        raise ValueError(
            f"unknown domain {name!r} — pick one of {', '.join(available_domains())}"
        )
    if name not in _domain_cache:
        _domain_cache[name] = _DOMAIN_FACTORIES[name]()
    return _domain_cache[name]


def _engines(name: str) -> tuple[KnowledgeGraph, KnowledgeBase]:
    if name not in _engine_cache:
        _engine_cache[name] = domain(name).build()
    return _engine_cache[name]


# --- the serializable, verifier-checked result --------------------------------


@dataclass(frozen=True)
class GroundedEvidence:
    """One cited record's provenance, serialized inline so an agent needs no
    second round-trip to trace a claim to its source."""

    id: str
    source: str
    locator_kind: str
    locator_parts: tuple[tuple[str, str], ...]
    ingested_at: str
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source": self.source,
            "locator": {
                "kind": self.locator_kind,
                "parts": [[label, value] for label, value in self.locator_parts],
                "render": ", ".join(f"{k} {v}" for k, v in self.locator_parts),
            },
            "ingested_at": self.ingested_at,
            "text": self.text,
        }


@dataclass(frozen=True)
class GroundedClaim:
    """A claim with its boundary verifier verdict and its full provenance."""

    text: str
    verified: bool
    support: tuple[GroundedEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "verified": self.verified,
            "support": [e.to_dict() for e in self.support],
        }


@dataclass(frozen=True)
class GroundedResult:
    """A grounded answer (or an explicit refusal) ready to cross the protocol
    boundary: the routing decision, the verified claims with provenance, and — for
    a refusal — the reason, carried so a refusal can never become an answer."""

    domain: str
    question: str
    route_kind: str
    route_reason: str
    grounded: bool
    refused: bool
    refusal: str | None
    claims: tuple[GroundedClaim, ...]

    @property
    def all_verified(self) -> bool:
        return all(claim.verified for claim in self.claims)

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain,
            "question": self.question,
            "route": {"kind": self.route_kind, "reason": self.route_reason},
            "grounded": self.grounded,
            "refused": self.refused,
            "refusal": self.refusal,
            "claims": [claim.to_dict() for claim in self.claims],
            "all_verified": self.all_verified,
        }


@dataclass(frozen=True)
class GroundedAssertion:
    """One additive assertion (resolution or mention) touching a record — the
    inspectable 'why is this evidence connected' trail of the ER layer."""

    kind: str  # "resolution" | "mention"
    a: str
    b: str
    confidence: float
    reason: str
    score: float | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "kind": self.kind,
            "a": self.a,
            "b": self.b,
            "confidence": self.confidence,
            "reason": self.reason,
        }
        if self.score is not None:
            out["score"] = self.score
        return out


# --- the tools ----------------------------------------------------------------


def verify_claims(
    answer: Answer,
    graph: KnowledgeGraph,
    claim_shapes: tuple[ClaimShape, ...],
) -> tuple[bool, ...]:
    """Live-verify each of an answer's claims with the eval's ``is_supported`` +
    the domain's claim shapes — the same structural check the harness gates on,
    run here at the boundary. The single source of truth for the verify loop the
    chat surface and the agent layer both use."""
    nodes: dict[str, Node] = {node.id: node for node in graph.nodes}
    return tuple(
        is_supported(claim, nodes, graph, claim_shapes) for claim in answer.claims
    )


def _evidence(record: EvidenceRecord) -> GroundedEvidence:
    locator = record.origin.locator
    return GroundedEvidence(
        id=record.id,
        source=record.origin.source,
        locator_kind=locator.kind,
        locator_parts=locator.parts,
        ingested_at=record.origin.ingested_at,
        text=record.text,
    )


def serialize_answer(
    answer: Answer,
    graph: KnowledgeGraph,
    claim_shapes: tuple[ClaimShape, ...],
    *,
    domain: str,
    question: str,
    route: Route,
) -> GroundedResult:
    """Project an :class:`Answer` into a serializable, verifier-checked
    :class:`GroundedResult` — the boundary projection (ADR 0022).

    Each claim is live-verified with ``is_supported``; support is sorted by id so
    the output is deterministic across hash seeds; a refusal is carried explicitly
    so it can never be rendered as an answer. This is the *only* place an answer
    crosses into agent-facing form, so the boundary's fidelity (Unit 5,
    ``tests/test_boundary.py``) is a property of this one function.
    """
    verdicts = verify_claims(answer, graph, claim_shapes)
    claims = tuple(
        GroundedClaim(
            text=claim.text,
            verified=verdict,
            support=tuple(
                _evidence(record)
                for record in sorted(claim.support, key=lambda rec: rec.id)
            ),
        )
        for claim, verdict in zip(answer.claims, verdicts, strict=True)
    )
    refused = not answer.is_grounded
    return GroundedResult(
        domain=domain,
        question=question,
        route_kind=route.kind,
        route_reason=route.reason,
        grounded=answer.is_grounded,
        refused=refused,
        refusal=(answer.refusal or REFUSAL_MESSAGE) if refused else None,
        claims=claims,
    )


def ground(domain_name: str, question: str) -> GroundedResult:
    """Route ``question`` in ``domain_name`` and return a verifier-checked,
    serializable grounded result. A refusal is carried explicitly — it can never
    be rendered as an answer across the boundary (ADR 0022)."""
    dom = domain(domain_name)
    graph, kb = _engines(domain_name)
    route, answer = dom.route(question, graph, kb)
    return serialize_answer(
        answer,
        graph,
        dom.claim_shapes,
        domain=domain_name,
        question=question,
        route=route,
    )


def assertions(domain_name: str, record_id: str) -> list[GroundedAssertion]:
    """The additive resolution/mention assertions touching ``record_id`` — the
    reversible, inspectable provenance of the entity-resolution layer."""
    graph, _ = _engines(domain_name)
    trail: list[GroundedAssertion] = []
    for resolution in graph.resolutions:
        if record_id in (resolution.node_a, resolution.node_b):
            trail.append(_resolution_assertion(resolution))
    for mention in graph.mentions:
        if record_id in (mention.chunk, mention.node):
            trail.append(_mention_assertion(mention))
    return trail


def _resolution_assertion(resolution: Resolution) -> GroundedAssertion:
    return GroundedAssertion(
        kind="resolution",
        a=resolution.node_a,
        b=resolution.node_b,
        confidence=resolution.confidence,
        reason=resolution.reason,
        score=resolution.score,
    )


def _mention_assertion(mention: Mention) -> GroundedAssertion:
    return GroundedAssertion(
        kind="mention",
        a=mention.chunk,
        b=mention.node,
        confidence=mention.confidence,
        reason=mention.reason,
    )
