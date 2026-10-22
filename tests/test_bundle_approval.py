"""Tests for verifiable approvals (spec 0145, ADR 0035).

The load-bearing property: an approval binds a KEY to EXACT BYTES (the
sealed root) — the forged challenge bundle cannot borrow the honest one's
approval, and a tampered-and-re-sealed bundle invalidates prior approvals
automatically. Approvals inform; policies enforce (four-eyes = one rule);
checking stays pure stdlib.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tessera.bundle.approval import (
    APPROVAL_FORMAT,
    ApprovalCheck,
    ApprovalFormatError,
    check_approval,
)
from tessera.bundle.cli import verify_main
from tessera.bundle.format import compute_root, leaf_manifest, seal
from tessera.bundle.policy import (
    PolicyError,
    evaluate_policy,
    validate_policy,
)
from tessera.bundle.verify import verify_bundle

REPO = Path(__file__).resolve().parents[1]
HONEST = REPO / "data" / "challenge" / "honest.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"

_HAVE_NACL = importlib.util.find_spec("nacl") is not None
_needs_sign = pytest.mark.skipif(not _HAVE_NACL, reason="needs the 'sign' extra")


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _root(bundle: dict[str, object]) -> str:
    return compute_root(leaf_manifest(bundle))


def _artifact(
    root: str, *, note: str | None = None, at: str | None = None
) -> dict[str, object]:
    """A shape-valid artifact with a dummy signature — enough to exercise
    every check that fires BEFORE signature verification."""
    return {
        "format": {"name": APPROVAL_FORMAT, "major": 1},
        "approves_root": root,
        "note": note,
        "at": at,
        "approver": {"algorithm": "ed25519", "public_key": "ab" * 32},
        "signature": "cd" * 64,
    }


def _keygen(tmp_path: Path, name: str) -> tuple[Path, str]:
    from tessera.bundle.signing import generate_keypair

    key = tmp_path / f"{name}.key"
    public = generate_keypair(key)
    return key, public


def _check(approval: ApprovalCheck) -> ApprovalCheck:
    return approval  # readability helper for synthesized checks


def _valid_check(key: str) -> ApprovalCheck:
    return ApprovalCheck(
        approves_root="sha256:" + "0" * 64,
        approver=key,
        valid=True,
        problem=None,
        note=None,
        at=None,
    )


# --- the exact-bytes binding (stdlib, no crypto needed to reach it) ---------------


def test_approval_binds_to_exact_bytes_root_mismatch_named() -> None:
    """THE property: the honest bundle's approval is INVALID against the
    forged bundle — root mismatch, named — before any signature math."""
    honest_root = _root(_load(HONEST))
    forged_root = _root(_load(FORGED))
    assert honest_root != forged_root
    check = check_approval(_artifact(honest_root), forged_root)
    assert not check.valid
    assert check.problem is not None
    assert "approves a different bundle" in check.problem
    assert "exact bytes" in check.problem


def test_reseal_invalidates_prior_approvals() -> None:
    """Tamper + re-seal moves the root; an approval of the old root reads
    invalid against the recomputed root of the descendant."""
    bundle = _load(HONEST)
    old_root = _root(bundle)
    result = bundle["result"]
    assert isinstance(result, dict)
    result["question"] = str(result["question"]) + " (edited)"
    resealed = seal({k: v for k, v in bundle.items() if k != "integrity"})
    check = check_approval(_artifact(old_root), _root(resealed))
    assert not check.valid and check.problem is not None
    assert "approves a different bundle" in check.problem


def test_bad_signature_is_named() -> None:
    root = _root(_load(HONEST))
    check = check_approval(_artifact(root), root)
    assert not check.valid
    assert check.problem is not None
    assert "signature does not verify" in check.problem


def test_malformed_artifacts_raise_named_errors() -> None:
    root = _root(_load(HONEST))
    with pytest.raises(ApprovalFormatError, match="not an approval artifact"):
        check_approval({"format": {"name": "something"}}, root)
    broken = _artifact(root)
    broken["signature"] = "zz"
    with pytest.raises(ApprovalFormatError, match="not valid hex"):
        check_approval(broken, root)
    short = _artifact(root)
    short["signature"] = "cd" * 10
    with pytest.raises(ApprovalFormatError, match="length"):
        check_approval(short, root)


def test_verify_reports_malformed_approval_as_named_invalid() -> None:
    """Through verify_bundle, a malformed artifact becomes a named invalid
    entry — never a crash, never a silent drop — and does not change the
    bundle's own verdict."""
    bundle = _load(HONEST)
    report = verify_bundle(bundle, approvals=[{"format": {"name": "junk"}}])
    assert report.verdict == "PASS"  # approvals inform, never alter
    assert len(report.approvals) == 1
    assert not report.approvals[0].valid
    problem = report.approvals[0].problem
    assert problem is not None and "malformed approval artifact" in problem


# --- policy enforcement (synthesized checks; no crypto needed) --------------------


def test_policy_four_eyes_counting() -> None:
    bundle = _load(HONEST)
    base = verify_bundle(bundle)
    policy = validate_policy(
        {
            "name": "four-eyes",
            "version": 1,
            "rules": {"approvals": {"require": 2, "distinct_approvers": True}},
        }
    )
    one = replace(base, approvals=(_valid_check("aa" * 32),))
    result = evaluate_policy(policy, bundle, one)
    assert not result.compliant
    assert "1 distinct valid approval(s)" in result.checks[0].detail

    duplicated = replace(
        base, approvals=(_valid_check("aa" * 32), _valid_check("aa" * 32))
    )
    result = evaluate_policy(policy, bundle, duplicated)
    assert not result.compliant  # the same key twice is one set of eyes

    two = replace(base, approvals=(_valid_check("aa" * 32), _valid_check("bb" * 32)))
    assert evaluate_policy(policy, bundle, two).compliant


def test_policy_allowed_approvers_excludes_outsiders() -> None:
    bundle = _load(HONEST)
    base = verify_bundle(bundle)
    policy = validate_policy(
        {
            "name": "named-approvers",
            "version": 1,
            "rules": {"approvals": {"require": 1, "allowed_approvers": ["aa" * 32]}},
        }
    )
    outsider = replace(base, approvals=(_valid_check("bb" * 32),))
    result = evaluate_policy(policy, bundle, outsider)
    by_rule = {c.rule: c for c in result.checks}
    assert not by_rule["approvals.allowed_approvers"].ok
    assert "outside the allowed list" in by_rule["approvals.allowed_approvers"].detail
    assert not by_rule["approvals.require"].ok  # outsiders never count


def test_policy_requiring_approvals_fails_closed_without_any() -> None:
    """Verify run without --approval against an approvals policy → violation,
    never a vacuous pass."""
    bundle = _load(HONEST)
    report = verify_bundle(bundle)
    policy = validate_policy(
        {"name": "p", "version": 1, "rules": {"approvals": {"require": 1}}}
    )
    result = evaluate_policy(policy, bundle, report)
    assert not result.compliant
    assert "0 valid approval(s)" in result.checks[0].detail


def test_policy_unknown_approvals_rule_refuses() -> None:
    with pytest.raises(PolicyError, match="unknown approvals rule"):
        validate_policy(
            {"name": "p", "version": 1, "rules": {"approvals": {"requier": 1}}}
        )
    with pytest.raises(PolicyError, match="positive integer"):
        validate_policy(
            {"name": "p", "version": 1, "rules": {"approvals": {"require": 0}}}
        )


# --- end to end with real keys (needs the 'sign' extra) ---------------------------


@_needs_sign
def test_end_to_end_four_eyes(tmp_path: Path) -> None:
    """keygen ×2 → approve ×2 → verify --approval ×2 --policy four-eyes →
    COMPLIANT exit 0; with one approval only → exit 5."""
    from tessera.bundle.approval import build_approval
    from tessera.bundle.canonical import canonical_bytes

    key1, pub1 = _keygen(tmp_path, "mgr1")
    key2, pub2 = _keygen(tmp_path, "mgr2")
    bundle_path = tmp_path / "decision.tsb"
    bundle_path.write_bytes(HONEST.read_bytes())
    bundle = _load(bundle_path)

    a1 = tmp_path / "a1.json"
    a2 = tmp_path / "a2.json"
    a1.write_bytes(
        canonical_bytes(build_approval(bundle, key1, note="quarterly review")) + b"\n"
    )
    a2.write_bytes(canonical_bytes(build_approval(bundle, key2)) + b"\n")

    policy_path = tmp_path / "four-eyes.json"
    policy_path.write_text(
        json.dumps(
            {
                "name": "four-eyes",
                "version": 1,
                "rules": {
                    "require_rederived": True,
                    "approvals": {
                        "require": 2,
                        "distinct_approvers": True,
                        "allowed_approvers": [pub1, pub2],
                    },
                },
            }
        )
    )

    assert (
        verify_main(
            [
                str(bundle_path),
                "--approval",
                str(a1),
                "--approval",
                str(a2),
                "--policy",
                str(policy_path),
            ]
        )
        == 0
    )
    assert (
        verify_main(
            [str(bundle_path), "--approval", str(a1), "--policy", str(policy_path)]
        )
        == 5
    )


@_needs_sign
def test_cli_approve_writes_and_never_overwrites(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tessera.bundle.cli import approve_main

    key, pub = _keygen(tmp_path, "mgr")
    bundle_path = tmp_path / "d.tsb"
    bundle_path.write_bytes(HONEST.read_bytes())
    out = tmp_path / "d.approval.json"

    assert approve_main([str(bundle_path), "--key", str(key), "-o", str(out)]) == 0
    assert pub in capsys.readouterr().out
    artifact = _load(out)
    check = check_approval(artifact, _root(_load(bundle_path)))
    assert check.valid and check.approver == pub

    assert approve_main([str(bundle_path), "--key", str(key), "-o", str(out)]) == 2
    assert "already exists" in capsys.readouterr().err


@_needs_sign
def test_verify_json_carries_approvals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tessera.bundle.approval import build_approval
    from tessera.bundle.canonical import canonical_bytes

    key, pub = _keygen(tmp_path, "mgr")
    bundle = _load(HONEST)
    a = tmp_path / "a.json"
    a.write_bytes(canonical_bytes(build_approval(bundle, key, at="2026-07-18")) + b"\n")
    bundle_path = tmp_path / "d.tsb"
    bundle_path.write_bytes(HONEST.read_bytes())

    assert verify_main([str(bundle_path), "--json", "--approval", str(a)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["approvals"][0]["valid"] is True
    assert payload["approvals"][0]["approver"] == pub
    assert payload["approvals"][0]["at"] == "2026-07-18"


def test_unreadable_approval_file_is_a_cli_file_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert verify_main([str(HONEST), "--approval", str(tmp_path / "missing.json")]) == 4
    assert "cannot read approval" in capsys.readouterr().err


def test_approval_check_path_is_stdlib_only() -> None:
    """Checking approvals must not pull the sign extra (the leak-guard)."""
    script = (
        "import sys\n"
        "import tessera.bundle.approval\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'nacl', 'numpy'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'approval pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
