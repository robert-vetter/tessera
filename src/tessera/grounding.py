"""The grounding engine — Tessera's smallest honest core.

This module is deliberately general and data-free: it defines what evidence, a
claim, and an answer *are*, and how a question becomes a grounded answer. The
demo data lives in :mod:`tessera.knowledge` so the engine stays vertical-neutral
(see the principles in ``CLAUDE.md``).

Two non-negotiable principles are enforced here, not just hoped for:

- **Provenance is mandatory.** A :class:`Claim` cannot be constructed without at
  least one supporting :class:`EvidenceRecord`. There is no code path that emits
  a claim without a trace back to its evidence.
- **Groundedness over fluency.** :func:`answer` returns a principled refusal
  when the knowledge base supports nothing, rather than inventing a response.

It is intentionally deterministic and LLM-free: a skeleton that proves the path
*question -> evidence -> grounded answer with provenance -> render* before any
real data, model, or graph arrives in later phases.
"""

from __future__ import annotations

from dataclasses import dataclass

REFUSAL_MESSAGE = "I don't have enough evidence to answer that."


@dataclass(frozen=True)
class Locator:
    """A modality-agnostic pointer to *where within a source* evidence sits.

    Deliberately a single, kind-tagged shape rather than per-modality fields, so
    one ``Origin.locator`` field serves every source type without ever being
    restructured. A structured row is ``kind="table-row"`` with parts
    ``(("table", "I_Customer"), ("row", "12"))``; a document span (arriving in
    Unit 2) is ``kind="doc-span"`` with parts ``(("page", "3"), ("line", "10"),
    ("chunk", "2"))``. Downstream code renders ``parts`` uniformly and never
    branches on ``kind`` — which is exactly what keeps the representation
    forward-compatible. See ``docs/adr/0002-*`` for the rejected alternatives.
    """

    kind: str
    parts: tuple[tuple[str, str], ...]

    @classmethod
    def table_row(cls, table: str, row: int) -> Locator:
        """Locator for a row of a structured table (1-based row number)."""
        return cls(kind="table-row", parts=(("table", table), ("row", str(row))))

    def render(self) -> str:
        return ", ".join(f"{label} {value}" for label, value in self.parts)


@dataclass(frozen=True)
class Origin:
    """Where a piece of evidence came from — enough to reconstruct provenance.

    ``source`` is a human-readable source identifier (e.g.
    ``"salt_synthetic/I_Customer.csv"``); ``locator`` pins the spot within it;
    ``ingested_at`` is the data snapshot's date (not wall-clock), so provenance
    metadata stays deterministic and reproducible.
    """

    source: str
    locator: Locator
    ingested_at: str


@dataclass(frozen=True)
class EvidenceRecord:
    """A single piece of source evidence, with enough origin to trace it.

    ``id`` is a stable handle (derived from the source's natural key, so it is
    reproducible across ingestion runs); ``origin`` carries the traceable
    provenance metadata; ``text`` is the supporting snippet itself. There is no
    way to construct a record without an origin — Pillar 1's "no information
    without a retrievable origin" holds by construction.
    """

    id: str
    origin: Origin
    text: str

    @property
    def source(self) -> str:
        """A readable one-line origin, source plus in-source locator."""
        return f"{self.origin.source} ({self.origin.locator.render()})"


@dataclass(frozen=True)
class Claim:
    """A statement in an answer, bound to the evidence that justifies it.

    Provenance is mandatory by construction: constructing a ``Claim`` with no
    supporting records raises :class:`ValueError`, so a claim without a trace
    back to its evidence is unrepresentable.
    """

    text: str
    support: tuple[EvidenceRecord, ...]

    def __post_init__(self) -> None:
        if not self.support:
            raise ValueError(
                f"Claim must cite at least one evidence record: {self.text!r}"
            )


@dataclass(frozen=True)
class Fact:
    """A demo knowledge entry: a claim plus the question keywords that trigger it.

    A fact matches when every keyword appears (case-insensitively) in the
    question. This is an honest, deterministic matcher for the Phase 0 skeleton
    — not natural-language understanding.
    """

    keywords: tuple[str, ...]
    claim: Claim

    def matches(self, question: str) -> bool:
        haystack = question.lower()
        return all(keyword.lower() in haystack for keyword in self.keywords)


@dataclass(frozen=True)
class KnowledgeBase:
    """The evidence and facts an answer may draw on."""

    records: tuple[EvidenceRecord, ...]
    facts: tuple[Fact, ...]


@dataclass(frozen=True)
class Answer:
    """The result of a question: either grounded claims or a refusal.

    Exactly one mode holds: if ``refusal`` is set, ``claims`` is empty, and vice
    versa.
    """

    question: str
    claims: tuple[Claim, ...]
    refusal: str | None

    @property
    def is_grounded(self) -> bool:
        return self.refusal is None and bool(self.claims)

    def render(self) -> str:
        """Render the answer as text, with each claim's provenance visible."""
        lines = [f"Q: {self.question}", ""]
        if not self.is_grounded:
            lines.append(self.refusal or REFUSAL_MESSAGE)
            return "\n".join(lines)
        for claim in self.claims:
            lines.append(f"- {claim.text}")
            for record in claim.support:
                lines.append(f'    ↳ {record.source} — "{record.text}"')
        return "\n".join(lines)


def answer(question: str, kb: KnowledgeBase) -> Answer:
    """Answer ``question`` using only what ``kb`` supports.

    Collects the claims of every fact whose keywords match the question. If none
    match, returns a principled refusal rather than guessing.
    """
    claims = tuple(fact.claim for fact in kb.facts if fact.matches(question))
    if not claims:
        return Answer(question=question, claims=(), refusal=REFUSAL_MESSAGE)
    return Answer(question=question, claims=claims, refusal=None)
