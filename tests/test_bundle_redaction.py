"""Tests for verifiable redaction (spec 0149, ADR 0039).

The unit exists to let a receipt leave the building without its evidence.
That is only safe if one property holds absolutely:

    Redaction can hide, but it can never upgrade a verdict.

Most of what follows tests that from the attacker's side.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.cli import redact_main
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.format import compute_root, leaf_manifest
from tessera.bundle.policy import PolicyError, evaluate_policy, validate_policy
from tessera.bundle.redact import (
    RedactionError,
    cited_ids,
    is_redacted,
    keep_closure,
    redact,
    withheld_ids,
)
from tessera.bundle.verify import verify_bundle

REPO = Path(__file__).resolve().parents[1]
HONEST = REPO / "data" / "challenge" / "honest.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"
DEMO = REPO / "data" / "redacted" / "honest-public.tsb"
JS = REPO / "verifier" / "js" / "tessera-verify.mjs"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _stored_root(bundle: dict[str, object]) -> str:
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    root = integrity["root"]
    assert isinstance(root, str)
    return root


# --- the property that makes redaction useful --------------------------------------


def test_the_root_survives_redaction() -> None:
    """The whole point: withheld content contributes its commitment, so the
    manifest and root recompute bit-for-bit identically."""
    original = _load(HONEST)
    redacted = redact(original)
    assert _stored_root(redacted) == _stored_root(original)
    integrity = redacted["integrity"]
    assert isinstance(integrity, dict)
    leaves = integrity["leaves"]
    assert isinstance(leaves, dict)
    assert compute_root(leaf_manifest(redacted, leaves)) == _stored_root(original)
    assert not verify_bundle(redacted).integrity_problems


def test_an_approval_of_the_original_still_validates_on_the_redacted_copy(
    tmp_path: Path,
) -> None:
    """Because the root is preserved, a sign-off made before redaction still
    verifies afterwards — the auditor checks the same signature."""
    import importlib.util

    if importlib.util.find_spec("nacl") is None:
        pytest.skip("needs the 'sign' extra to create an approval")
    from tessera.bundle.approval import build_approval
    from tessera.bundle.signing import generate_keypair

    key = tmp_path / "approver.key"
    public = generate_keypair(key)
    original = _load(HONEST)
    artifact = build_approval(original, key)

    report = verify_bundle(redact(original), approvals=[artifact])
    assert len(report.approvals) == 1
    assert report.approvals[0].valid is True
    assert report.approvals[0].approver == public


def test_claims_still_re_derive_when_their_evidence_is_kept() -> None:
    """The default keeps cited records plus one relation hop, which is what
    the entity/aggregate grammars walk — so the findings stay verifiable."""
    report = verify_bundle(redact(_load(HONEST)))
    assert report.claims
    assert all(check.rederived for check in report.claims)
    assert not report.semantic_problems


def test_redaction_shrinks_the_receipt() -> None:
    original = _load(HONEST)
    redacted = redact(original)
    assert len(canonical_bytes(redacted)) < len(canonical_bytes(original)) / 2


# --- the safety property, from the attacker's side ---------------------------------


def test_hiding_the_falsifying_evidence_never_yields_pass() -> None:
    """THE pin. A forger redacts exactly the evidence that exposes the lie.
    Every hash still checks out and the root is intact — and the verdict is
    still not PASS: each affected claim is visibly not re-derived."""
    forged = _load(FORGED)
    hidden = redact(forged, keep=set())
    report = verify_bundle(hidden)

    assert not report.integrity_problems  # the envelope is perfect
    assert report.verdict != "PASS"
    assert report.exit_code == 3  # degraded, not a pass
    assert report.claims and not any(check.rederived for check in report.claims)
    assert report.withheld


def test_a_forgery_whose_evidence_is_kept_still_fails() -> None:
    """Redacting the *rest* of the corpus does not launder a forgery whose
    cited evidence is still present: it fails exactly as before."""
    forged = _load(FORGED)
    assert verify_bundle(forged).verdict == "FAIL"
    assert verify_bundle(redact(forged)).verdict == "FAIL"


def test_a_redacted_bundle_can_never_report_pass() -> None:
    """Even a perfectly honest, fully re-deriving redacted bundle degrades:
    the verifier states that content was withheld rather than implying it
    checked everything."""
    report = verify_bundle(redact(_load(HONEST)))
    assert report.verdict == "DEGRADED"
    assert report.exit_code == 3
    assert report.answer_rederives is None  # not performed on a partial corpus


def test_withholding_the_whole_graph_degrades_to_integrity_only() -> None:
    original = _load(HONEST)
    stripped = redact(original, keep=set())
    closure = stripped["evidence_closure"]
    assert isinstance(closure, dict)
    closure["graph"] = {"redacted": True}
    report = verify_bundle(stripped)
    assert report.taxonomy == "INTEGRITY-ONLY"
    assert report.verdict == "DEGRADED"


# --- the mechanics -----------------------------------------------------------------


def test_keep_closure_covers_cited_records_and_one_hop() -> None:
    original = _load(HONEST)
    cited = cited_ids(original)
    keep = keep_closure(original, hops=1)
    assert cited <= keep
    assert len(keep) > len(cited)  # the hop actually pulled neighbours in


def test_withheld_nodes_keep_their_id_so_citations_resolve() -> None:
    redacted = redact(_load(HONEST))
    assert withheld_ids(redacted)
    assert is_redacted(redacted)
    closure = redacted["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    withheld = [n for n in nodes if n.get("redacted")]
    assert withheld
    assert all(node["record"]["id"] for node in withheld)
    # ...and nothing else: no text, no origin, no attributes travel.
    assert all(set(node) == {"redacted", "record"} for node in withheld)
    assert all(set(node["record"]) == {"id"} for node in withheld)


def test_redacting_an_unsealed_bundle_is_refused() -> None:
    unsealed = {k: v for k, v in _load(HONEST).items() if k != "integrity"}
    with pytest.raises(RedactionError, match="unsealed"):
        redact(unsealed)


def test_redacting_nothing_is_refused() -> None:
    bundle = _load(HONEST)
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    everything = {node["record"]["id"] for node in nodes}
    with pytest.raises(RedactionError, match="withhold nothing"):
        redact(bundle, keep=everything, withhold_kb=False)


def test_the_format_section_is_untouched() -> None:
    """Bumping the minor would move the root — the finding that corrected
    spec 0149 D2. Redaction is self-describing through its markers."""
    original = _load(HONEST)
    assert redact(original)["format"] == original["format"]


# --- governance --------------------------------------------------------------------


def test_policy_can_refuse_redacted_evidence() -> None:
    redacted = redact(_load(HONEST))
    report = verify_bundle(redacted)
    policy = validate_policy(
        {
            "name": "full-evidence",
            "version": 1,
            "rules": {"redaction": {"allow": False}},
        }
    )
    result = evaluate_policy(policy, redacted, report)
    assert not result.compliant
    assert "requires the complete evidence" in result.checks[0].detail

    complete = _load(HONEST)
    assert evaluate_policy(policy, complete, verify_bundle(complete)).compliant


def test_policy_can_bound_how_much_is_withheld() -> None:
    redacted = redact(_load(HONEST))
    report = verify_bundle(redacted)
    policy = validate_policy(
        {"name": "p", "version": 1, "rules": {"redaction": {"max_withheld": 5}}}
    )
    assert not evaluate_policy(policy, redacted, report).compliant


def test_unknown_redaction_rule_fails_closed() -> None:
    with pytest.raises(PolicyError, match="unknown redaction rule"):
        validate_policy(
            {"name": "p", "version": 1, "rules": {"redaction": {"alow": False}}}
        )


# --- the committed demo + the CLI --------------------------------------------------


def test_committed_demo_preserves_the_public_root() -> None:
    """The committed redacted copy of the challenge bundle carries the same
    root as the honest original — a stranger can check that in one line."""
    assert DEMO.is_file()
    demo = _load(DEMO)
    assert _stored_root(demo) == _stored_root(_load(HONEST))
    report = verify_bundle(demo)
    assert not report.integrity_problems
    assert report.verdict == "DEGRADED"
    assert all(check.rederived for check in report.claims)


def test_cli_redacts_and_refuses_to_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "d.tsb"
    source.write_bytes(bundle_bytes(build_bundle("business", "Compare Acme and Beta.")))
    out = tmp_path / "d.redacted.tsb"

    assert redact_main([str(source), "-o", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "UNCHANGED" in printed
    assert _stored_root(_load(out)) == _stored_root(_load(source))

    assert redact_main([str(source), "-o", str(out)]) == 2
    assert "already exists" in capsys.readouterr().err


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node (installed in CI)")
def test_the_independent_verifier_agrees_on_redaction(tmp_path: Path) -> None:
    """A format change only one implementation understands would undo spec
    0148 — so the second verifier handles withheld leaves too, and agrees."""
    redacted = redact(_load(HONEST))
    path = tmp_path / "r.tsb"
    path.write_bytes(canonical_bytes(redacted) + b"\n")
    proc = subprocess.run(
        ["node", str(JS), str(path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout, proc.stderr
    report = json.loads(proc.stdout)
    assert not report["integrity_problems"]  # the root survives there too
    assert len(report["withheld"]) == len(verify_bundle(redacted).withheld)
    assert proc.returncode == verify_bundle(redacted).exit_code == 3
    assert report["verdict"] != "PASS-PARTIAL"  # never a pass, in either language
