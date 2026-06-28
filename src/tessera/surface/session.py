"""A conversational session over the measured verticals.

The session owns what a conversation needs and an answer alone does not:
which vertical is active, each vertical's graph/KB (built lazily, once), the
last answer's numbered claims so provenance can be *explored* rather than
only printed, and the live verifier verdicts that make the trust signal a
fact, not a slogan — every claim is re-checked with the same
``is_supported`` + vertical claim shapes the eval harness uses (ADR 0011).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tessera.agent.grounded import domain, verify_claims
from tessera.eval.metrics import ClaimShape
from tessera.graph import KnowledgeGraph, Mention, Resolution
from tessera.grounding import Answer, Claim, KnowledgeBase
from tessera.routing import Route

if TYPE_CHECKING:
    from collections.abc import Callable

    RouteFn = Callable[[str, KnowledgeGraph, KnowledgeBase], tuple[Route, Answer]]


@dataclass(frozen=True)
class TurnResult:
    """One question's outcome: the route, the answer, and live verification."""

    vertical: str
    route: Route
    answer: Answer
    verified: tuple[bool, ...]  # one verdict per claim, same order

    @property
    def all_verified(self) -> bool:
        return all(self.verified)


@dataclass
class _VerticalContext:
    """A vertical's lazily built engines plus its declared claim grammars."""

    build: Callable[[], tuple[KnowledgeGraph, KnowledgeBase]]
    route: RouteFn
    claim_shapes: tuple[ClaimShape, ...]
    _engines: tuple[KnowledgeGraph, KnowledgeBase] | None = None

    def engines(self) -> tuple[KnowledgeGraph, KnowledgeBase]:
        if self._engines is None:
            self._engines = self.build()
        return self._engines


def _context_from_domain(name: str) -> _VerticalContext:
    """Build a chat context from the shared grounded-tool domain registry, so the
    set of verticals and how they route + verify has one source of truth (the
    agent layer); the chat surface adds only the stateful, exploratory concerns."""
    dom = domain(name)
    return _VerticalContext(
        build=dom.build, route=dom.route, claim_shapes=dom.claim_shapes
    )


def _business_context() -> _VerticalContext:
    return _context_from_domain("business")


def _devex_context() -> _VerticalContext:
    return _context_from_domain("devex")


VERTICALS: tuple[str, ...] = ("business", "devex")


@dataclass
class ChatSession:
    """The conversational state: active vertical, engines, last turn."""

    vertical: str = "business"
    _contexts: dict[str, _VerticalContext] = field(default_factory=dict)
    last_turn: TurnResult | None = None

    def _context(self, name: str) -> _VerticalContext:
        if name not in self._contexts:
            factory = {
                "business": _business_context,
                "devex": _devex_context,
            }[name]
            self._contexts[name] = factory()
        return self._contexts[name]

    def switch(self, vertical: str) -> None:
        if vertical not in VERTICALS:
            raise ValueError(
                f"unknown vertical {vertical!r} — pick one of {', '.join(VERTICALS)}"
            )
        self.vertical = vertical

    def ask(self, question: str) -> TurnResult:
        """Route the question in the active vertical and live-verify the answer."""
        context = self._context(self.vertical)
        graph, kb = context.engines()
        decision, answer = context.route(question, graph, kb)
        verified = verify_claims(answer, graph, context.claim_shapes)
        self.last_turn = TurnResult(
            vertical=self.vertical, route=decision, answer=answer, verified=verified
        )
        return self.last_turn

    # --- provenance exploration ------------------------------------------------
    def claim(self, number: int) -> Claim:
        """Claim ``number`` (1-based) of the last answer."""
        if self.last_turn is None or not self.last_turn.answer.claims:
            raise LookupError("no answer to explore yet — ask a question first")
        claims = self.last_turn.answer.claims
        if not 1 <= number <= len(claims):
            raise LookupError(f"claim number must be 1..{len(claims)}")
        return claims[number - 1]

    def assertions_about(self, record_id: str) -> list[Resolution | Mention]:
        """The additive assertions (resolutions/mentions) touching a cited
        record — the inspectable 'why is this evidence connected' trail."""
        graph, _ = self._context(self.vertical).engines()
        trail: list[Resolution | Mention] = [
            r for r in graph.resolutions if record_id in (r.node_a, r.node_b)
        ]
        trail.extend(m for m in graph.mentions if record_id in (m.chunk, m.node))
        return trail
