"""Tests for the bounded soundness theorem (spec 0147, ADR 0037).

The most important tests here are the ones that would catch a *vacuous*
proof: an enumeration that silently skips states, a checker that has lost
its ability to detect unsoundness, or a model that has drifted away from
the verifier it claims to describe. "PROVED" is only worth reading next to
these.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.proof import universe as uni
from tessera.proof.bridge import check_fidelity, real_verdict
from tessera.proof.check import (
    VERIFIERS,
    Certificate,
    check_universe,
    render_certificate,
    run_proof,
)
from tessera.proof.cli import main as proof_main
from tessera.proof.model import (
    Claim,
    Kind,
    Question,
    State,
    verify_claims_only,
    verify_reexecution,
    verify_trusting,
)

REPO = Path(__file__).resolve().parents[1]
CERTIFICATE = REPO / "data" / "proof" / "certificate.json"


@pytest.fixture(scope="module")
def certificate() -> Certificate:
    return run_proof()


# --- the enumeration is actually exhaustive ---------------------------------------


@pytest.mark.parametrize("bounds", uni.DEFAULT_UNIVERSES)
def test_enumeration_matches_its_own_size_formula(bounds: uni.Bounds) -> None:
    """A silently truncated enumeration would make the theorem vacuous, so
    the count is derived twice — by formula and by walking — and compared."""
    assert sum(1 for _ in uni.states(bounds)) == uni.count(bounds)


def test_universes_are_not_trivially_small() -> None:
    total = sum(uni.count(b) for b in uni.DEFAULT_UNIVERSES)
    assert total > 250_000  # the published bound must stay meaningful


def test_universe_includes_dangling_citations_and_both_questions() -> None:
    """The universe must contain the shapes an attacker actually reaches:
    a claim citing a record that was deleted, and every question."""
    sample = list(uni.states(uni.UNIVERSE_A))
    assert any(
        any(i >= len(s.records) for c in s.claims for i in c.cited) for s in sample
    )
    assert {s.question for s in sample} == set(Question)
    assert {c.kind for s in sample for c in s.claims} == set(Kind)


# --- the theorem -------------------------------------------------------------------


def test_no_false_pass_exists(certificate: Certificate) -> None:
    """THE theorem: every state the re-executing verifier accepts is honest."""
    rows = [r for r in certificate.results if r.verifier == "re-execution"]
    assert rows, "the real verifier must be checked"
    for row in rows:
        assert row.counterexample is None
        assert row.passes > 0, "a verifier that accepts nothing proves nothing"


def test_negative_controls_are_refuted_with_counterexamples(
    certificate: Certificate,
) -> None:
    """A checker that cannot find unsoundness proves nothing. Both flawed
    verifiers must be caught, with concrete counterexamples."""
    for key in ("control-trusting", "control-claims-only"):
        rows = [r for r in certificate.results if r.verifier == key]
        assert rows
        assert any(r.counterexample is not None for r in rows), key
    assert certificate.proved


def test_proved_requires_the_controls_to_fail() -> None:
    """If a control were (wrongly) sound, the certificate must NOT read
    proved — pinned by constructing that situation directly."""
    from dataclasses import replace

    cert = run_proof((uni.UNIVERSE_B,))
    assert cert.proved
    patched = replace(
        cert,
        results=tuple(
            replace(r, counterexample=None) if r.verifier.startswith("control-") else r
            for r in cert.results
        ),
    )
    assert not patched.proved


def test_trusting_control_accepts_a_plainly_false_claim() -> None:
    """The control models what an integrity-only receipt does: it believes
    the recorded verdict. Here is the one-line reason that is unsound."""
    lie = State(
        records=(2,),
        question=Question.TOTAL,
        claims=(Claim(Kind.SUM, (0,), asserted=99, recorded_verified=True),),
    )
    assert verify_trusting(lie) is True  # the forgery passes
    assert verify_reexecution(lie) is False  # re-execution catches it
    assert not lie.is_honest()


def test_claims_only_control_accepts_a_true_claim_about_the_wrong_question() -> None:
    """The subtler control: every claim is genuinely true, but it is not the
    answer to the question the bundle packages."""
    misattached = State(
        records=(3,),
        question=Question.TOTAL,
        claims=(Claim(Kind.QUOTE, (0,), asserted=3, recorded_verified=True),),
    )
    assert verify_claims_only(misattached) is True
    assert verify_reexecution(misattached) is False
    assert not misattached.is_honest()


def test_honest_states_do_pass(certificate: Certificate) -> None:
    """Soundness without completeness would be trivial (reject everything).
    An honest state must actually pass."""
    honest = State(
        records=(1, 2),
        question=Question.TOTAL,
        claims=(Claim(Kind.SUM, (0, 1), asserted=3, recorded_verified=True),),
    )
    assert honest.is_honest()
    assert verify_reexecution(honest) is True


# --- fidelity to the shipping verifier --------------------------------------------


def test_model_agrees_with_the_real_verifier(certificate: Certificate) -> None:
    assert certificate.fidelity_checked > 20_000
    assert certificate.fidelity_disagreements == ()


def test_bridge_uses_the_real_grammars() -> None:
    """Spot-check the bridge against the shipping is_supported directly: a
    correct aggregate is supported, an inflated one is not, and a verbatim
    quote is supported."""
    assert real_verdict(Claim(Kind.SUM, (0, 1), 3, True), (1, 2)) is True
    assert real_verdict(Claim(Kind.SUM, (0, 1), 4, True), (1, 2)) is False
    assert real_verdict(Claim(Kind.QUOTE, (0,), 1, True), (1, 2)) is True
    assert real_verdict(Claim(Kind.QUOTE, (0,), 2, True), (1, 2)) is False


def test_fidelity_detects_a_deliberately_wrong_model() -> None:
    """If the model's semantics drifted from the implementation, the bridge
    must say so — proven by feeding it a claim whose model verdict is
    inverted."""

    class Inverted(Claim):
        def is_valid(self, records: tuple[int, ...]) -> bool:
            return not super().is_valid(records)

    bad = Inverted(Kind.SUM, (0,), 1, True)
    checked, problems = check_fidelity([(1,)], [bad])
    assert checked == 1
    assert len(problems) == 1


# --- the published artifact --------------------------------------------------------


def test_committed_certificate_matches_a_fresh_run(certificate: Certificate) -> None:
    from tessera.bundle.canonical import canonical_bytes

    assert CERTIFICATE.is_file(), "the certificate must be committed"
    assert CERTIFICATE.read_bytes() == canonical_bytes(certificate.to_dict()) + b"\n"


def test_render_states_the_bound_and_the_limits(certificate: Certificate) -> None:
    text = render_certificate(certificate)
    assert "BOUNDS" in text and "states" in text
    assert "WHAT THIS DOES NOT PROVE" in text
    assert "BOUNDED" in text
    assert "not verified" in text  # the implementation caveat, verbatim
    assert "REFUTED (as required)" in text
    assert text.rstrip().endswith("VERDICT: PROVED")


def test_cli_and_front_door(capsys: pytest.CaptureFixture[str]) -> None:
    assert proof_main([]) == 0
    assert "PROVED" in capsys.readouterr().out

    assert proof_main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["certificate"] == "tessera-bounded-soundness-1"
    assert payload["proved"] is True
    assert payload["fidelity"]["disagreements"] == []

    from tessera.cli import main as front_door

    assert front_door(["proof"]) == 0
    capsys.readouterr()


def test_every_declared_verifier_is_checked(certificate: Certificate) -> None:
    checked = {r.verifier for r in certificate.results}
    assert checked == {v.key for v in VERIFIERS}


def test_check_universe_rejects_a_truncated_enumeration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard that makes a vacuous proof impossible: if enumeration and
    formula disagree, the run must fail loudly."""

    original = uni.states

    def truncated(bounds: uni.Bounds):  # type: ignore[no-untyped-def]
        yield from list(original(bounds))[:10]

    monkeypatch.setattr(uni, "states", truncated)
    with pytest.raises(AssertionError, match="incomplete enumeration"):
        check_universe(uni.UNIVERSE_B, VERIFIERS[0])


def test_proof_is_deterministic_across_hash_seeds() -> None:
    script = (
        "import hashlib\n"
        "from tessera.bundle.canonical import canonical_bytes\n"
        "from tessera.proof.check import run_proof\n"
        "print(hashlib.sha256(canonical_bytes(run_proof().to_dict())).hexdigest())\n"
    )
    digests = set()
    for seed in ("0", "1", "42"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        digests.add(proc.stdout.strip())
    assert len(digests) == 1


def test_proof_path_is_stdlib_only() -> None:
    script = (
        "import sys\n"
        "import tessera.proof.check\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'nacl', 'numpy', 'z3'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'proof pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
