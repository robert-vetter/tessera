"""Cross-implementation conformance (spec 0148, ADR 0038).

Two verifiers written in different languages must agree on every case, or
the guarantee lives in one codebase rather than in the format. These tests
run the independent JavaScript implementation out-of-process over the whole
kit and check the differential contract — including the direction that
matters most: *the portable verifier must never bless something the
reference rejects for a reason it covers.*

The suite skips cleanly where Node is unavailable; CI installs it, so the
contract is enforced there.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.verify import verify_bundle

REPO = Path(__file__).resolve().parents[1]
JS = REPO / "verifier" / "js" / "tessera-verify.mjs"
JS_CORE = REPO / "verifier" / "js" / "verify-core.mjs"
KIT = REPO / "data" / "kit" / "expectations.json"
HONEST = REPO / "data" / "challenge" / "honest.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"
BRIEF = REPO / "data" / "chain" / "brief.tsb"

_HAVE_NODE = shutil.which("node") is not None
_needs_node = pytest.mark.skipif(not _HAVE_NODE, reason="needs Node (installed in CI)")


def _run_js(path: Path, *extra: str) -> tuple[int, Any]:
    proc = subprocess.run(
        ["node", str(JS), str(path), "--json", *extra],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def _materialise(bundle: dict[str, object], directory: Path) -> Path:
    path = directory / "case.tsb"
    path.write_bytes(canonical_bytes(bundle) + b"\n")
    return path


def _kit() -> Any:
    """The committed kit, read as the dynamic JSON document it is."""
    return json.loads(KIT.read_text(encoding="utf-8"))


# --- the artifact itself -----------------------------------------------------------


def test_kit_is_committed_and_describes_the_contract() -> None:
    kit = _kit()
    assert kit["kit"] == "tessera-cross-implementation-1"
    assert len(kit["cases"]) >= 20
    contract = " ".join(kit["contract"])
    assert "never rejects what the reference accepts" in contract
    assert "declines them" in contract


def test_the_two_non_portable_checks_are_named_not_hidden() -> None:
    """The portable verifier must state what it does not do — a silent scope
    gap would look like agreement while proving nothing. The scope lives in
    the core (spec 0150), which is the file both front ends share."""
    source = JS_CORE.read_text(encoding="utf-8")
    assert "answer re-derivation" in source
    assert "action re-derivation" in source
    assert "PASS-PARTIAL" in source


def test_the_core_has_no_imports_so_it_runs_anywhere() -> None:
    """One implementation, two front ends (spec 0150 D1): the core must stay
    dependency-free, or the browser build becomes a second implementation."""
    source = JS_CORE.read_text(encoding="utf-8")
    assert "\nimport " not in source  # no ES imports at all
    assert "require(" not in source
    # ...and specifically nothing from a runtime-only module. ("node:" also
    # appears as a manifest leaf prefix and in prose, so match the import.)
    assert 'from "node:' not in source


# --- the differential contract, case by case ---------------------------------------


@_needs_node
def test_kit_matches_a_fresh_cross_implementation_run() -> None:
    """The committed kit is byte-identical to a fresh generation, so the
    published cross-implementation result cannot drift from the code."""
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from build_conformance_kit import build  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    assert KIT.read_bytes() == canonical_bytes(build()) + b"\n"


@_needs_node
def test_differential_contract_holds_on_every_case() -> None:
    """THE test: no disagreement anywhere, and every case where the portable
    verifier stays silent while the reference fails is one it declines by
    design — proven per case, not asserted in prose."""
    violations = []
    for case in _kit()["cases"]:
        verdict, exit_code = case["js_verdict"], case["python_exit"]
        if verdict == "TAMPERED" and exit_code != 4:
            violations.append((case["case"], verdict, exit_code))
        if verdict == "FAIL" and exit_code not in (2, 4):
            violations.append((case["case"], verdict, exit_code))
        if (
            verdict == "PASS-PARTIAL"
            and exit_code in (2, 4)
            and not case["declined_by_design"]
        ):
            violations.append((case["case"], verdict, exit_code))
    assert not violations, f"cross-implementation disagreement: {violations}"


@_needs_node
def test_blind_spots_are_exactly_the_engine_bound_checks() -> None:
    """The declined cases must be precisely the attacks that need the router
    or the drafting pipeline — if that set grows, the scope table is wrong."""
    declined = {c["case"] for c in _kit()["cases"] if c["declined_by_design"]}
    assert declined == {
        "attack:question_swap",
        "attack:fabricated_render",
        "attack:wire_body_injection",
        "attack:wire_method_repoint",
        "attack:wire_slot_edit",
        "attack:outcome_forgery",
        "attack:approval_strip",
    }


# --- the headline behaviours -------------------------------------------------------


@_needs_node
def test_independent_verifier_agrees_on_the_challenge_pair() -> None:
    """The public challenge, judged by a second implementation: honest passes,
    forged fails with the same per-claim breakdown the reference produces."""
    code, honest = _run_js(HONEST)
    assert code == 0 and honest["verdict"] == "PASS-PARTIAL"

    code, forged = _run_js(FORGED)
    assert code == 2 and forged["verdict"] == "FAIL"
    js_rederived = [c["rederived"] for c in forged["claims"]]
    reference = verify_bundle(json.loads(FORGED.read_text(encoding="utf-8")))
    assert js_rederived == [c.rederived for c in reference.claims]


@_needs_node
def test_independent_verifier_walks_the_chain_recursively() -> None:
    code, report = _run_js(BRIEF)
    assert code == 0 and report["verdict"] == "PASS-PARTIAL"
    assert len(report["upstreams"]) == 2
    assert all(u["verdict"] == "PASS-PARTIAL" for u in report["upstreams"])


@_needs_node
def test_independent_verifier_catches_a_resealed_forgery(tmp_path: Path) -> None:
    """A re-sealed semantic edit — the attack integrity checking cannot see —
    is caught by the second implementation too."""
    from tessera.bundle.mutations import evidence_value_edit

    base = json.loads(
        bundle_bytes(
            build_bundle(
                "business", "Compare Müller Logistik and Nordwind Logistik totals."
            )
        )
    )
    mutant = evidence_value_edit(base).bundle
    code, report = _run_js(_materialise(mutant, tmp_path))
    assert code == 2 and report["verdict"] == "FAIL"
    assert not report["integrity_problems"]  # the hashes are perfect
    assert report["semantic_problems"]  # only re-execution sees it


@_needs_node
def test_independent_verifier_checks_a_detached_approval(tmp_path: Path) -> None:
    """Approvals are portable: the same artifact validates in JavaScript, and
    the forged bundle cannot borrow the honest bundle's approval."""
    import importlib.util

    if importlib.util.find_spec("nacl") is None:
        pytest.skip("needs the 'sign' extra to create an approval")
    from tessera.bundle.approval import build_approval
    from tessera.bundle.signing import generate_keypair

    key = tmp_path / "approver.key"
    public = generate_keypair(key)
    honest = json.loads(HONEST.read_text(encoding="utf-8"))
    artifact = tmp_path / "a.json"
    artifact.write_bytes(canonical_bytes(build_approval(honest, key)) + b"\n")

    code, report = _run_js(HONEST, "--approval", str(artifact))
    assert code == 0
    assert report["approvals"] == [{"valid": True, "approver": public, "problem": None}]

    _, forged = _run_js(FORGED, "--approval", str(artifact))
    assert forged["approvals"][0]["valid"] is False
    assert "different bundle" in forged["approvals"][0]["problem"]


@_needs_node
def test_independent_verifier_refuses_a_reserved_anchor(tmp_path: Path) -> None:
    bundle = json.loads(HONEST.read_text(encoding="utf-8"))
    bundle["anchor"] = {"log": "example"}
    code, report = _run_js(_materialise(bundle, tmp_path))
    assert code == 4 and report["verdict"] == "TAMPERED"
