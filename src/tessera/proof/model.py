"""The formal model of a trust bundle and its verifier (spec 0147).

Small enough to read in one sitting, faithful enough that its claim
semantics are differentially pinned to the shipping verifier
(:mod:`tessera.proof.bridge`). Everything the soundness theorem says is
said about *this* model; what that does and does not imply about the
implementation is stated in ``docs/PROOF.md`` and in the CLI output.

The model deliberately gives the attacker **maximum power**: there are no
hashes and no signatures in it at all. Anything an attacker could re-seal
or re-sign is simply assumed already re-sealed and re-signed, so a state
is judged purely on whether its content hangs together. That is the
strongest possible adversary — the "issuer" threat model of the
conformance benchmark, taken to its limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


#: Claim grammars the model covers, mirroring the two real shapes the
#: bridge evaluates: an aggregate recomputation and verbatim containment.
class Kind(Enum):
    SUM = "sum"  # "total net order value across N order(s): EUR X"
    QUOTE = "quote"  # the claim text is a cited record's text, verbatim


#: The questions a packaged corpus can answer, each with a canonical
#: answer the verifier re-derives (the model's router).
class Question(Enum):
    TOTAL = "total"  # one SUM claim over every record
    FIRST = "first"  # one QUOTE claim of the first record
    BOTH = "both"  # a two-claim answer: the total AND the first line quoted


@dataclass(frozen=True)
class Claim:
    """One recorded claim: its grammar, the records it cites, the value it
    asserts, and the verdict the bundle *records* for it."""

    kind: Kind
    cited: tuple[int, ...]
    asserted: int
    recorded_verified: bool

    def is_valid(self, records: tuple[int, ...]) -> bool:
        """Recompute the claim against the evidence it cites — the model's
        ``is_supported``.

        A citation to a record that is not packaged makes the claim
        unsupported (the real verifier's referential-integrity check).
        ``QUOTE`` mirrors the real containment grammar's ``any(...)``
        semantics: the quoted text must appear in *some* cited record, not
        in all of them.
        """
        if not self.cited:
            return False
        if any(index < 0 or index >= len(records) for index in self.cited):
            return False
        if self.kind is Kind.SUM:
            return self.asserted == sum(records[i] for i in self.cited)
        return any(self.asserted == records[i] for i in self.cited)


@dataclass(frozen=True)
class State:
    """A whole bundle: the packaged evidence, the packaged question, and
    the recorded answer (an ordered tuple of claims)."""

    records: tuple[int, ...]
    question: Question
    claims: tuple[Claim, ...]

    def canonical_claims(self) -> tuple[Claim, ...]:
        """The answer the packaged corpus actually yields for the packaged
        question — the model's deterministic router. Verification requires
        the recorded answer to equal this exactly (the real check (b))."""
        if not self.records:
            return ()
        total = Claim(
            kind=Kind.SUM,
            cited=tuple(range(len(self.records))),
            asserted=sum(self.records),
            recorded_verified=True,
        )
        first = Claim(
            kind=Kind.QUOTE,
            cited=(0,),
            asserted=self.records[0],
            recorded_verified=True,
        )
        if self.question is Question.TOTAL:
            return (total,)
        if self.question is Question.FIRST:
            return (first,)
        # A two-claim answer, so multi-claim answers are genuinely reachable:
        # without it a two-claim universe could never contain a passing state
        # and the theorem would hold there only vacuously.
        return (total, first)

    def is_honest(self) -> bool:
        """The property the theorem protects: every claim is genuinely
        supported by the evidence it cites, every recorded verdict equals
        the recomputed one, and the recorded answer is the one this corpus
        yields for this question. A state that is *not* honest asserts
        something false about its own packaged contents."""
        for claim in self.claims:
            if claim.is_valid(self.records) != claim.recorded_verified:
                return False
            if not claim.recorded_verified:
                return False
        return self.claims == self.canonical_claims()


# --- verifiers ---------------------------------------------------------------------
#
# The real verifier's model, plus the deliberately flawed controls that make
# "PROVED" falsifiable (spec 0147 D4). Each takes a state and returns True for
# PASS.


def verify_reexecution(state: State) -> bool:
    """The model of Tessera's verifier: recompute every claim from the
    packaged evidence, require the recorded verdicts to match *and* be
    true, and require the recorded answer to re-derive from the packaged
    corpus.

    This mirrors the real ``exit_code == 0`` condition: no semantic
    problems (no claim mismatch, the answer re-derives) and no degradation
    (no honestly-unverified claim).
    """
    for claim in state.claims:
        rederived = claim.is_valid(state.records)
        if rederived != claim.recorded_verified:
            return False  # recorded verdict disagrees with re-execution
        if not rederived:
            return False  # honestly unverified — degraded, never a PASS
    return state.claims == state.canonical_claims()


def verify_trusting(state: State) -> bool:
    """NEGATIVE CONTROL — believes the recorded verdict instead of
    recomputing it, which is exactly what an integrity-only receipt does
    once its hashes check out. The checker MUST refute this one."""
    return all(claim.recorded_verified for claim in state.claims) and bool(state.claims)


def verify_claims_only(state: State) -> bool:
    """NEGATIVE CONTROL — recomputes claims honestly but never checks that
    the recorded answer is the one the corpus yields, so a true claim
    attached to the wrong question (or an answer with claims dropped)
    passes. The checker MUST refute this one too."""
    return bool(state.claims) and all(
        claim.is_valid(state.records) == claim.recorded_verified
        and claim.recorded_verified
        for claim in state.claims
    )
