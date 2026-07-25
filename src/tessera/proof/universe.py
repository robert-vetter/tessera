"""Exhaustive enumeration of the bounded state universe (spec 0147).

The theorem is checked over *every* state in the universe, not over states
reached by some edit sequence. That is the point: because the universe is
closed under arbitrary rewriting, an attacker with unlimited re-sealing
and re-signing power can only ever produce a state that is already in it.
No completeness argument about an attack algebra is needed — the universe
is the closure.

Two bounds are enumerated in full. Their sizes are printed with every
result and committed in the certificate, so the scope of the claim always
travels with the claim.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import combinations, product

from tessera.proof.model import Claim, Kind, Question, State


@dataclass(frozen=True)
class Bounds:
    """One bounded universe: how many records, which values, how many
    claims, and the asserted-value domain."""

    name: str
    max_records: int
    values: tuple[int, ...]
    claims: int
    max_asserted: int

    def describe(self) -> str:
        return (
            f"{self.name}: ≤{self.max_records} record(s) with values "
            f"{{{','.join(str(v) for v in self.values)}}}, {self.claims} claim(s), "
            f"asserted values 0–{self.max_asserted}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "max_records": self.max_records,
            "values": list(self.values),
            "claims": self.claims,
            "max_asserted": self.max_asserted,
        }


#: Universe A — a single claim over up to three records. Wide value domain.
UNIVERSE_A = Bounds(
    name="A", max_records=3, values=(1, 2, 3, 4), claims=1, max_asserted=12
)
#: Universe B — two claims (so multi-claim answers and cross-claim forgeries
#: are covered) over up to two records.
UNIVERSE_B = Bounds(name="B", max_records=2, values=(1, 2, 3), claims=2, max_asserted=6)
#: A deeper bound, run with --deep: three claims, so three-way cross-claim
#: forgeries are covered. Narrower in the other dimensions to stay finite in
#: practice (~4.4M states, minutes rather than the 1.8 billion a naive
#: widening would cost — the trade is stated rather than hidden).
UNIVERSE_DEEP = Bounds(
    name="deep", max_records=2, values=(1, 2), claims=3, max_asserted=4
)

DEFAULT_UNIVERSES = (UNIVERSE_A, UNIVERSE_B)


def _corpora(bounds: Bounds) -> Iterator[tuple[int, ...]]:
    for size in range(1, bounds.max_records + 1):
        yield from product(bounds.values, repeat=size)


def _citation_sets(size: int) -> Iterator[tuple[int, ...]]:
    """Every non-empty subset of record indices, in canonical order, plus
    one dangling citation per size — a claim citing a record that is not
    packaged is a state an attacker can build (record deletion), so it
    belongs in the universe."""
    indices = range(size)
    for subset_size in range(1, size + 1):
        yield from combinations(indices, subset_size)
    yield (size,)  # dangling: cites a record index that does not exist


def _claims(bounds: Bounds, corpus_size: int) -> Iterator[Claim]:
    for kind in Kind:
        for cited in _citation_sets(corpus_size):
            for asserted in range(bounds.max_asserted + 1):
                for recorded in (True, False):
                    yield Claim(
                        kind=kind,
                        cited=cited,
                        asserted=asserted,
                        recorded_verified=recorded,
                    )


def states(bounds: Bounds) -> Iterator[State]:
    """Every state in the bounded universe. Deterministic order.

    Answers of **every length from 1 to ``bounds.claims``** are enumerated,
    not just the maximum: dropping a claim from an answer is something an
    attacker does, and a universe of fixed-length answers could not contain
    the honest states of shorter ones — which would make the theorem hold
    there only vacuously.
    """
    for records in _corpora(bounds):
        claim_space = list(_claims(bounds, len(records)))
        for question in Question:
            for length in range(1, bounds.claims + 1):
                for combo in product(claim_space, repeat=length):
                    yield State(records=records, question=question, claims=combo)


def count(bounds: Bounds) -> int:
    """The exact size of a universe, computed rather than measured, so the
    enumeration can be checked against it (an enumeration that silently
    skipped states would make the theorem vacuous)."""
    total = 0
    for size in range(1, bounds.max_records + 1):
        corpora = len(bounds.values) ** size
        citations = sum(_binomial(size, k) for k in range(1, size + 1)) + 1
        claims = len(Kind) * citations * (bounds.max_asserted + 1) * 2
        answers = sum(claims**length for length in range(1, bounds.claims + 1))
        total += corpora * len(Question) * answers
    return total


def _binomial(n: int, k: int) -> int:
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result
