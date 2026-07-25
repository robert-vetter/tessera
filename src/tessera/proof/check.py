"""The theorem runner (spec 0147).

Checks, over every state of a bounded universe:

    verify(S) = PASS  ⟹  S is honest

for the model of Tessera's verifier, and — mandatorily, in the same run —
for two deliberately flawed verifiers that **must** be refuted. A checker
that cannot find unsoundness proves nothing, so "PROVED" is only
meaningful next to a "REFUTED" it produced itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tessera.proof import universe as uni
from tessera.proof.bridge import Disagreement, check_fidelity
from tessera.proof.model import (
    Claim,
    State,
    verify_claims_only,
    verify_reexecution,
    verify_trusting,
)

Verifier = Callable[[State], bool]


@dataclass(frozen=True)
class VerifierUnderTest:
    key: str
    title: str
    check: Verifier
    must_be_sound: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "expected": "sound" if self.must_be_sound else "unsound (control)",
        }


VERIFIERS: tuple[VerifierUnderTest, ...] = (
    VerifierUnderTest(
        key="re-execution",
        title="Tessera: recompute claims, require the answer to re-derive",
        check=verify_reexecution,
        must_be_sound=True,
    ),
    VerifierUnderTest(
        key="control-trusting",
        title="CONTROL: trusts the recorded verdict (what integrity-only does)",
        check=verify_trusting,
        must_be_sound=False,
    ),
    VerifierUnderTest(
        key="control-claims-only",
        title="CONTROL: recomputes claims but never re-derives the answer",
        check=verify_claims_only,
        must_be_sound=False,
    ),
)


def _describe(state: State) -> dict[str, object]:
    return {
        "records": list(state.records),
        "question": state.question.value,
        "claims": [
            {
                "kind": claim.kind.value,
                "cited": list(claim.cited),
                "asserted": claim.asserted,
                "recorded_verified": claim.recorded_verified,
            }
            for claim in state.claims
        ],
    }


@dataclass(frozen=True)
class UniverseResult:
    """One verifier's result over one universe."""

    universe: str
    verifier: str
    states: int
    passes: int
    counterexample: dict[str, object] | None

    @property
    def sound(self) -> bool:
        return self.counterexample is None

    def to_dict(self) -> dict[str, object]:
        return {
            "universe": self.universe,
            "verifier": self.verifier,
            "states": self.states,
            "passes": self.passes,
            "sound": self.sound,
            "counterexample": self.counterexample,
        }


@dataclass(frozen=True)
class Certificate:
    """The whole machine-checked result: the theorem, its bounds, the
    per-universe outcomes, the negative controls, and the fidelity bridge."""

    theorem: str
    scope: tuple[str, ...]
    bounds: tuple[uni.Bounds, ...]
    results: tuple[UniverseResult, ...]
    fidelity_checked: int
    fidelity_disagreements: tuple[Disagreement, ...]

    @property
    def proved(self) -> bool:
        """PROVED requires three things at once: the real verifier's model
        is sound everywhere, BOTH controls were refuted (so the checker
        demonstrably can fail), and the model agrees with the shipping
        implementation on every claim it covers."""
        real_sound = all(r.sound for r in self.results if r.verifier == "re-execution")
        controls_refuted = all(
            not r.sound for r in self.results if r.verifier.startswith("control-")
        )
        return real_sound and controls_refuted and not self.fidelity_disagreements

    def to_dict(self) -> dict[str, object]:
        return {
            "certificate": "tessera-bounded-soundness-1",
            "theorem": self.theorem,
            "scope": list(self.scope),
            "bounds": [b.to_dict() for b in self.bounds],
            "verifiers": [v.to_dict() for v in VERIFIERS],
            "results": [r.to_dict() for r in self.results],
            "fidelity": {
                "claims_checked_against_implementation": self.fidelity_checked,
                "disagreements": [d.to_dict() for d in self.fidelity_disagreements],
            },
            "proved": self.proved,
        }


THEOREM = (
    "For every state S in the enumerated universe: if the verifier returns "
    "PASS for S, then S is honest — every claim's asserted content is "
    "derivable from the evidence it cites, every recorded verdict equals the "
    "recomputed one, and the recorded answer is exactly the one the packaged "
    "corpus yields for the packaged question."
)

SCOPE = (
    "BOUNDED: the universes below are enumerated in full; larger states are "
    "not covered.",
    "This proves a property of a MODEL. The model's claim semantics are "
    "differentially checked against the shipping verifier over the same "
    "domain; the Python implementation itself (hashing, JSON, I/O) is not "
    "verified.",
    "Model fidelity is TESTED, not proven — that gap is inherent to this "
    "technique and is named rather than glossed.",
    "Says nothing about truth in the world: honesty here means a claim "
    "follows from the evidence packaged with it.",
)


def check_universe(bounds: uni.Bounds, verifier: VerifierUnderTest) -> UniverseResult:
    """Enumerate the universe and check the implication for every state."""
    passes = 0
    total = 0
    counterexample: dict[str, object] | None = None
    for state in uni.states(bounds):
        total += 1
        if not verifier.check(state):
            continue
        passes += 1
        if not state.is_honest() and counterexample is None:
            counterexample = _describe(state)
    expected = uni.count(bounds)
    if total != expected:
        raise AssertionError(
            f"enumeration produced {total} states, the formula says {expected} — "
            "an incomplete enumeration would make the theorem vacuous"
        )
    return UniverseResult(
        universe=bounds.name,
        verifier=verifier.key,
        states=total,
        passes=passes,
        counterexample=counterexample,
    )


def _fidelity_inputs(bounds: uni.Bounds) -> tuple[list[tuple[int, ...]], list[Claim]]:
    corpora = list(uni._corpora(bounds))
    largest = max(len(c) for c in corpora)
    claims = list(uni._claims(bounds, largest))
    return corpora, claims


def run_proof(bounds: tuple[uni.Bounds, ...] = uni.DEFAULT_UNIVERSES) -> Certificate:
    """Run the whole thing: every verifier over every universe, plus the
    fidelity bridge."""
    results = [check_universe(b, verifier) for b in bounds for verifier in VERIFIERS]
    checked = 0
    disagreements: list[Disagreement] = []
    for b in bounds:
        corpora, claims = _fidelity_inputs(b)
        count, problems = check_fidelity(corpora, claims)
        checked += count
        disagreements.extend(problems)
    return Certificate(
        theorem=THEOREM,
        scope=SCOPE,
        bounds=tuple(bounds),
        results=tuple(results),
        fidelity_checked=checked,
        fidelity_disagreements=tuple(disagreements),
    )


# --- rendering --------------------------------------------------------------------


def render_certificate(cert: Certificate) -> str:
    lines = [
        "Bounded soundness theorem — machine-checked, exhaustively",
        "",
        "THEOREM",
        f"  {cert.theorem}",
        "",
        "BOUNDS (every state enumerated, not sampled)",
    ]
    for b in cert.bounds:
        lines.append(f"  {b.describe()} → {uni.count(b):,} states")
    lines.append("")
    lines.append("RESULT")
    for verifier in VERIFIERS:
        rows = [r for r in cert.results if r.verifier == verifier.key]
        checked = sum(r.states for r in rows)
        passed = sum(r.passes for r in rows)
        sound = all(r.sound for r in rows)
        if verifier.must_be_sound:
            verdict = "PROVED — no false PASS exists" if sound else "REFUTED"
        else:
            verdict = "REFUTED (as required)" if not sound else "NOT REFUTED — BAD"
        lines.append(f"  [{verdict}] {verifier.key}: {verifier.title}")
        lines.append(f"      {checked:,} states checked · {passed:,} accepted as PASS")
        counter = next((r.counterexample for r in rows if r.counterexample), None)
        if counter is not None:
            lines.append(f"      counterexample: {counter}")
    lines.append("")
    lines.append("FIDELITY TO THE SHIPPING VERIFIER")
    lines.append(
        f"  {cert.fidelity_checked:,} model claims re-evaluated by the real "
        f"is_supported · {len(cert.fidelity_disagreements)} disagreement(s)"
    )
    lines.append("")
    lines.append("WHAT THIS DOES NOT PROVE")
    for note in cert.scope:
        lines.append(f"  · {note}")
    lines.append("")
    lines.append(f"VERDICT: {'PROVED' if cert.proved else 'NOT PROVED'}")
    return "\n".join(lines)
