"""Tests for the Verification Gap benchmark (spec 0146, ADR 0036).

A comparative benchmark is only worth its bytes if it can be attacked. The
pins here are therefore mostly *against the author's own interest*:

- no method may flag an honest bundle (no false positives anywhere);
- every method must detect the classic byte-level tampering it is designed
  for (the baselines are not built to lose);
- under the outside-tamperer model the signature-based methods must detect
  every re-sealed attack — i.e. Tessera's re-execution adds no detection
  power there, and the test says so;
- re-execution must MISS the replay attack (a PASS is not a recency claim)
  while the runtime-attestation method catches it;
- NOT-APPLICABLE outcomes must never count toward a score.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.conformance.attacks import ATTACKS, FAMILIES, base_bundles
from tessera.conformance.cli import main as conformance_main
from tessera.conformance.methods import (
    DETECTED,
    ISSUER,
    METHODS,
    MISSED,
    NOT_APPLICABLE,
    OUTSIDER,
)
from tessera.conformance.runner import Scorecard, run_benchmark

REPO = Path(__file__).resolve().parents[1]
SCORECARD = REPO / "data" / "conformance" / "scorecard.json"

_RESEALED_FAMILIES = ("semantic", "action", "chain")
_NON_REEXECUTING = (
    "hash-manifest",
    "signed-receipt",
    "policy-bound-receipt",
    "syntactic-envelope",
)


@pytest.fixture(scope="module")
def card() -> Scorecard:
    return run_benchmark()


# --- soundness: no false positives -------------------------------------------------


def test_no_method_flags_an_honest_bundle() -> None:
    """THE soundness pin. Every method must pass every honest base bundle
    under both threat models — a method that cries wolf would score well on
    this benchmark for the worst possible reason."""
    bases = base_bundles()
    for name, bundle in bases.items():
        for method in METHODS:
            for threat in (OUTSIDER, ISSUER):
                outcome = method.check(bundle, bundle, threat)
                assert outcome == MISSED, (
                    f"{method.key} flagged the honest {name} bundle ({threat})"
                )


def test_every_attack_actually_forges_something() -> None:
    """An attack that silently no-ops would be a hole that reads as a win."""
    bases = base_bundles()
    for attack in ATTACKS:
        base = bases[attack.base]
        assert attack.forge(base) != base, f"{attack.key} did not change the bundle"


# --- anti-strawman: the baselines are not built to lose ---------------------------


def test_every_method_detects_classic_byte_tampering(card: Scorecard) -> None:
    """Each method detects the attack class its own literature targets:
    a corrupted manifest leaf and a corrupted root, under both models."""
    for method in METHODS:
        for attack_key in ("leaf_tamper", "root_mismatch"):
            for threat in (OUTSIDER, ISSUER):
                assert card.outcome(method.key, attack_key, threat) == DETECTED, (
                    f"{method.key} missed {attack_key} — a baseline that weak "
                    "would make this benchmark worthless"
                )


def test_outsider_model_signatures_detect_every_resealed_attack(
    card: Scorecard,
) -> None:
    """Under an outside tamperer, an unforgeable attestation over the root
    catches every re-sealed forgery — so re-execution adds NO detection
    power in this model. Pinned because it is the honest half of the story.
    """
    for attack in ATTACKS:
        if attack.family not in _RESEALED_FAMILIES:
            continue
        for method_key in ("signed-receipt", "policy-bound-receipt"):
            assert card.outcome(method_key, attack.key, OUTSIDER) == DETECTED, (
                f"{method_key} should detect {attack.key} under the outsider model"
            )


def test_hash_manifest_misses_section_smuggling(card: Scorecard) -> None:
    """A manifest that hashes leaves does not commit to the section set —
    the exact hole Tessera's own M20/M21 audit found in its integrity layer
    and fixed. Kept visible as a real, source-honest difference."""
    assert card.outcome("hash-manifest", "extra_top_section", ISSUER) == MISSED
    assert card.outcome("re-execution", "extra_top_section", ISSUER) == DETECTED


# --- the gap itself ----------------------------------------------------------------


def test_issuer_model_is_the_gap(card: Scorecard) -> None:
    """The headline result: when the issuer is the forger, no
    non-re-executing method detects ANY semantic, action or chain forgery —
    and re-execution detects all of them."""
    for attack in ATTACKS:
        if attack.family not in _RESEALED_FAMILIES:
            continue
        for method_key in _NON_REEXECUTING:
            assert card.outcome(method_key, attack.key, ISSUER) == MISSED
        assert card.outcome("re-execution", attack.key, ISSUER) == DETECTED


def test_undeclared_dependency_matches_the_papers_own_scope(card: Scorecard) -> None:
    """The runtime-attestation method misses a dependency outside the
    declared envelope — which is exactly the scope its source states for
    that invariant — while re-execution catches it via referential
    integrity."""
    assert card.outcome("syntactic-envelope", "undeclared_dependency", ISSUER) == MISSED
    assert card.outcome("re-execution", "undeclared_dependency", ISSUER) == DETECTED


def test_re_execution_loses_the_replay_attack(card: Scorecard) -> None:
    """Tessera's own documented limit, measured: a PASS is a statement about
    claims and evidence, never about recency. The runtime-attestation
    method's freshness invariant catches what re-execution cannot."""
    for threat in (OUTSIDER, ISSUER):
        assert card.outcome("re-execution", "stale_contract_replay", threat) == MISSED
        assert (
            card.outcome("syntactic-envelope", "stale_contract_replay", threat)
            == DETECTED
        )


def test_policy_swap_is_not_applicable_to_re_execution(card: Scorecard) -> None:
    """Tessera keeps policy OUT of the artifact by design (ADR 0034), so the
    attack does not exist against it — scored N/A, never counted as a win."""
    assert card.outcome("re-execution", "policy_swap", ISSUER) == NOT_APPLICABLE
    assert card.outcome("policy-bound-receipt", "policy_swap", ISSUER) == DETECTED
    detected, applicable = card.tally("re-execution", ISSUER, "declaration")
    assert (detected, applicable) == (1, 1)  # the N/A cell is excluded


def test_tallies_are_consistent(card: Scorecard) -> None:
    for method in METHODS:
        for threat in (OUTSIDER, ISSUER):
            overall = card.tally(method.key, threat)
            per_family = [card.tally(method.key, threat, f) for f in FAMILIES]
            assert overall[0] == sum(d for d, _ in per_family)
            assert overall[1] == sum(a for _, a in per_family)


# --- the published artifact --------------------------------------------------------


def test_committed_scorecard_matches_a_fresh_run(card: Scorecard) -> None:
    """The published numbers can never drift from the code that produced
    them (the challenge-artifact pattern)."""
    from tessera.bundle.canonical import canonical_bytes

    assert SCORECARD.is_file(), "the scorecard artifact must be committed"
    assert SCORECARD.read_bytes() == canonical_bytes(card.to_dict()) + b"\n"


def test_cli_renders_and_round_trips(capsys: pytest.CaptureFixture[str]) -> None:
    assert conformance_main([]) == 0
    text = capsys.readouterr().out
    assert "OUTSIDE tamperer" in text
    assert "ISSUER itself" in text
    # The honest half is rendered before the flattering one.
    assert text.index("OUTSIDE tamperer") < text.index("ISSUER itself")
    assert "No vendor is named or scored." in text

    assert conformance_main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["benchmark"] == "tessera-verification-gap-1"
    assert len(payload["cells"]) == len(METHODS) * len(ATTACKS) * 2
    assert payload["totals"][ISSUER]["re-execution"]["semantic"] == [7, 7]
    assert payload["totals"][ISSUER]["signed-receipt"]["semantic"] == [0, 7]


def test_front_door_dispatches_conformance() -> None:
    from tessera.cli import main as front_door

    assert front_door(["conformance"]) == 0


def test_benchmark_is_deterministic_across_hash_seeds() -> None:
    script = (
        "import hashlib\n"
        "from tessera.bundle.canonical import canonical_bytes\n"
        "from tessera.conformance.runner import run_benchmark\n"
        "data = canonical_bytes(run_benchmark().to_dict())\n"
        "print(hashlib.sha256(data).hexdigest())\n"
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


def test_conformance_path_is_stdlib_only() -> None:
    script = (
        "import sys\n"
        "import tessera.conformance.runner\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'nacl', 'numpy'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'conformance pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)


def test_no_vendor_is_named_in_a_score() -> None:
    """The benchmark grades methods. Product names may appear in prose
    describing a *published method*, never as a graded row key."""
    for method in METHODS:
        assert method.key.islower()
        assert " " not in method.key
