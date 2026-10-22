"""Tests for the issuance ledger (spec 0151, ADR 0041).

Merkle proofs are easy to get subtly wrong, so correctness is established
**exhaustively** — every entry of every log size, every consistency pair —
rather than by spot checks. The rest of the file is adversarial: a
rewritten history must not produce a consistency proof, an unrecorded
receipt must not produce an inclusion proof, and a proof must never be
allowed to vouch for its own head.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.cli import attest_main, verify_main
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.policy import PolicyError, evaluate_policy, validate_policy
from tessera.bundle.verify import verify_bundle
from tessera.ledger.store import (
    Head,
    Ledger,
    LedgerError,
    check_consistency,
    check_inclusion,
)
from tessera.ledger.tree import (
    consistency_proof,
    inclusion_proof,
    leaf_hash,
    node_hash,
    root,
    verify_consistency,
    verify_inclusion,
)

REPO = Path(__file__).resolve().parents[1]
HONEST = REPO / "data" / "challenge" / "honest.tsb"


def _leaves(count: int) -> list[bytes]:
    return [leaf_hash(f"sha256:{i:064x}") for i in range(count)]


# --- the proofs, exhaustively -------------------------------------------------------


def test_every_inclusion_proof_verifies_for_every_size() -> None:
    for size in range(1, 40):
        leaves = _leaves(size)
        head = root(leaves)
        for index in range(size):
            path = inclusion_proof(leaves, index)
            assert verify_inclusion(leaves[index], index, size, path, head), (
                size,
                index,
            )


def test_every_consistency_pair_verifies() -> None:
    for size in range(1, 40):
        leaves = _leaves(size)
        head = root(leaves)
        for old in range(1, size + 1):
            proof = consistency_proof(leaves, old)
            assert verify_consistency(old, root(leaves[:old]), size, head, proof), (
                old,
                size,
            )


def test_hashing_is_domain_separated() -> None:
    """A leaf must never be presentable as an interior node — the classic
    second-preimage attack on a naive Merkle tree."""
    left, right = _leaves(2)
    interior = node_hash(left, right)
    assert leaf_hash("x") != node_hash(leaf_hash("x"), leaf_hash("x"))
    assert interior != leaf_hash(interior.hex())


# --- adversarial --------------------------------------------------------------------


def test_rewriting_history_cannot_produce_a_consistency_proof() -> None:
    """THE pin: an operator who edits an earlier entry cannot reconcile the
    two heads."""
    leaves = _leaves(8)
    tampered = list(leaves)
    tampered[2] = leaf_hash("sha256:" + "ab" * 32)
    assert not verify_consistency(
        4, root(leaves[:4]), 8, root(tampered), consistency_proof(tampered, 4)
    )


def test_deleting_an_entry_cannot_produce_a_consistency_proof() -> None:
    leaves = _leaves(8)
    without = leaves[:3] + leaves[4:]
    assert not verify_consistency(
        5, root(leaves[:5]), 7, root(without), consistency_proof(without, 5)
    )


def test_a_truncated_or_padded_proof_is_refused() -> None:
    leaves = _leaves(8)
    head = root(leaves)
    proof = consistency_proof(leaves, 4)
    assert not verify_consistency(4, root(leaves[:4]), 8, head, proof[:-1])
    assert not verify_consistency(4, root(leaves[:4]), 8, head, [*proof, proof[0]])


def test_a_leaf_that_was_never_appended_has_no_proof() -> None:
    leaves = _leaves(8)
    ghost = leaf_hash("sha256:" + "ff" * 32)
    assert not verify_inclusion(ghost, 3, 8, inclusion_proof(leaves, 3), root(leaves))


# --- the log ------------------------------------------------------------------------


def test_an_unrecorded_receipt_cannot_be_proved(tmp_path: Path) -> None:
    """The completeness question, answered: a decision the operator never
    logged has no inclusion proof at all."""
    log = Ledger(tmp_path / "issued.log")
    for i in range(4):
        log.append(f"sha256:{i:064x}")
    with pytest.raises(LedgerError, match="never recorded"):
        log.prove("sha256:" + "ee" * 32)


def test_appending_the_same_receipt_twice_is_refused(tmp_path: Path) -> None:
    log = Ledger(tmp_path / "issued.log")
    log.append("sha256:" + "11" * 32)
    with pytest.raises(LedgerError, match="already entry 0"):
        log.append("sha256:" + "11" * 32)


def test_inclusion_is_checked_against_the_head_the_verifier_supplies(
    tmp_path: Path,
) -> None:
    """A proof that vouches for its own head is self-attestation — the exact
    failure mode this project exists to answer."""
    log = Ledger(tmp_path / "issued.log")
    roots = [f"sha256:{i:064x}" for i in range(6)]
    for value in roots:
        log.append(value)
    proof = log.prove(roots[2])

    assert check_inclusion(proof, roots[2], log.head()) is None
    # A different head of the same size must not be satisfiable.
    forged_head = Head(size=log.head().size, root="sha256:" + "00" * 32)
    assert check_inclusion(proof, roots[2], forged_head) is not None
    # ...nor a proof presented for a different receipt.
    assert "not for this bundle" in str(check_inclusion(proof, roots[3], log.head()))


def test_consistency_artifact_round_trips(tmp_path: Path) -> None:
    log = Ledger(tmp_path / "issued.log")
    for i in range(9):
        log.append(f"sha256:{i:064x}")
    assert check_consistency(log.consistency(5)) is None
    broken = log.consistency(5)
    broken["path"] = []
    assert "rewritten" in str(check_consistency(broken))


# --- CLI + governance ---------------------------------------------------------------


def test_attest_then_verify_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle_path = tmp_path / "d.tsb"
    bundle_path.write_bytes(bundle_bytes(build_bundle("business", "Compare Acme.")))
    ledger_path = tmp_path / "issued.log"

    assert attest_main([str(bundle_path), "--ledger", str(ledger_path)]) == 0
    assert "UNCHANGED" not in capsys.readouterr().out  # attest never edits the bundle

    head = str(Ledger(ledger_path).head())
    proof = tmp_path / "d.tsb.inclusion.json"
    assert proof.is_file()

    assert (
        verify_main([str(bundle_path), "--inclusion", str(proof), "--head", head]) == 0
    )
    assert "included in the issuance log" in capsys.readouterr().out


def test_verify_without_a_head_reports_not_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No head, no claim — never a silent pass."""
    bundle_path = tmp_path / "d.tsb"
    bundle_path.write_bytes(bundle_bytes(build_bundle("business", "Compare Acme.")))
    attest_main([str(bundle_path), "--ledger", str(tmp_path / "l.log")])
    capsys.readouterr()
    verify_main(
        [str(bundle_path), "--inclusion", str(tmp_path / "d.tsb.inclusion.json")]
    )
    assert "no --head supplied" in capsys.readouterr().out


def test_attesting_does_not_touch_the_bundle(tmp_path: Path) -> None:
    """Like an approval, the proof is detached: no root moves, so signatures
    and approvals stay valid."""
    bundle_path = tmp_path / "d.tsb"
    original = bundle_bytes(build_bundle("business", "Compare Acme."))
    bundle_path.write_bytes(original)
    attest_main([str(bundle_path), "--ledger", str(tmp_path / "l.log")])
    assert bundle_path.read_bytes() == original


def test_policy_can_require_a_completeness_proof(tmp_path: Path) -> None:
    bundle = json.loads(HONEST.read_text(encoding="utf-8"))
    report = verify_bundle(bundle)
    policy = validate_policy(
        {
            "name": "logged",
            "version": 1,
            "rules": {"ledger": {"require_inclusion": True}},
        }
    )
    result = evaluate_policy(policy, bundle, report)
    assert not result.compliant  # fail-closed: no proof checked is not a pass
    assert "no inclusion proof was checked" in result.checks[0].detail

    from dataclasses import replace

    included = replace(report, inclusion="included")
    assert evaluate_policy(policy, bundle, included).compliant


def test_unknown_ledger_rule_fails_closed() -> None:
    with pytest.raises(PolicyError, match="unknown ledger rule"):
        validate_policy(
            {"name": "p", "version": 1, "rules": {"ledger": {"require_inclusio": True}}}
        )


# --- cross-implementation -----------------------------------------------------------


def test_the_independent_verifier_checks_the_same_proofs(tmp_path: Path) -> None:
    """A protocol addition only one implementation understands would undo
    ADR 0038 — so inclusion verification lives in the shared JS core too."""
    import shutil

    if shutil.which("node") is None:
        pytest.skip("needs Node (installed in CI)")

    log = Ledger(tmp_path / "l.log")
    roots = [f"sha256:{i:064x}" for i in range(11)]
    for value in roots:
        log.append(value)
    head = log.head()
    cases = [
        {"proof": log.prove(value), "root": value, "head": str(head)} for value in roots
    ]
    mismatched = log.prove(roots[2])
    cases.append({"proof": mismatched, "root": roots[5], "head": str(head)})
    payload = tmp_path / "cases.json"
    payload.write_bytes(canonical_bytes(cases) + b"\n")

    script = (
        'import { checkInclusionProof } from "%s";\n'
        'import { readFileSync } from "node:fs";\n'
        'const cases = JSON.parse(readFileSync(process.argv[1], "utf8"));\n'
        "console.log(JSON.stringify(cases.map((c) => "
        "checkInclusionProof(c.proof, c.root, c.head) === null)));"
    ) % (REPO / "verifier" / "js" / "verify-core.mjs")
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(payload)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    js = json.loads(proc.stdout)
    python = [check_inclusion(c["proof"], c["root"], head) is None for c in cases]  # type: ignore[arg-type]
    assert js == python
    assert python[-1] is False  # the mismatched case is refused in both
