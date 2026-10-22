"""Tests for trust policies (spec 0144, ADR 0034).

The load-bearing properties: fail-closed parsing (a typo'd rule refuses to
evaluate, never silently passes), every rule's violated case carries a named
detail, the exit precedence 4 > 2 > 5 > 3 > 0 (a policy can never upgrade a
broken or lying bundle), and the scoped meaning of COMPLIANT is pinned
verbatim.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.bundle.cli import verify_main
from tessera.bundle.emit import build_action_bundle, build_bundle, bundle_bytes
from tessera.bundle.policy import (
    SCOPE_LINE,
    PolicyError,
    chain_depth,
    evaluate_policy,
    load_policy,
    render_policy,
    validate_policy,
)
from tessera.bundle.verify import VerifyReport, verify_bundle

REPO = Path(__file__).resolve().parents[1]
BRIEF = REPO / "data" / "chain" / "brief.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"
POLICIES = REPO / "policies"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _policy(rules: dict[str, object]) -> dict[str, object]:
    return {"name": "t", "version": 1, "rules": rules}


@pytest.fixture(scope="module")
def brief() -> dict[str, object]:
    return _load(BRIEF)


@pytest.fixture(scope="module")
def brief_report() -> VerifyReport:
    return verify_bundle(_load(BRIEF))


# --- fail-closed parsing ----------------------------------------------------------


def test_unknown_rule_refuses_to_evaluate() -> None:
    """THE fail-closed property: a misspelled guardrail is a refusal, never a
    silent pass."""
    with pytest.raises(PolicyError, match="unknown rule"):
        validate_policy(_policy({"require_signd": True}))


def test_unknown_nested_and_malformed_rules_refuse() -> None:
    with pytest.raises(PolicyError, match="unknown actions rule"):
        validate_policy(_policy({"actions": {"alow": False}}))
    with pytest.raises(PolicyError, match="unknown chain rule"):
        validate_policy(_policy({"chain": {"max_dpeth": 1}}))
    with pytest.raises(PolicyError, match="must be true/false"):
        validate_policy(_policy({"require_signed": "yes"}))
    with pytest.raises(PolicyError, match="non-empty list"):
        validate_policy(_policy({"allowed_signers": []}))
    with pytest.raises(PolicyError, match="non-negative integer"):
        validate_policy(_policy({"chain": {"max_depth": -1}}))
    with pytest.raises(PolicyError, match="must be an integer"):
        validate_policy(
            {"name": "t", "version": True, "rules": {"require_signed": True}}
        )


def test_unreadable_policy_refuses(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(PolicyError, match="cannot read"):
        load_policy(missing)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(PolicyError, match="not valid JSON"):
        load_policy(bad)


def test_committed_policies_are_valid() -> None:
    for path in sorted(POLICIES.glob("*.json")):
        load_policy(path)  # must not raise


# --- rule outcomes ----------------------------------------------------------------


def test_read_only_policy_compliant_on_the_brief(
    brief: dict[str, object],
    brief_report: VerifyReport,
) -> None:
    policy = load_policy(POLICIES / "read-only.json")
    report = evaluate_policy(policy, brief, brief_report)
    assert report.compliant
    assert all(check.ok for check in report.checks)
    rendered = render_policy(report)
    assert "COMPLIANT" in rendered
    assert SCOPE_LINE in rendered  # the scoped meaning, pinned verbatim
    assert "not legal compliance" in SCOPE_LINE


def test_signed_chain_policy_names_the_unsigned_links(
    brief: dict[str, object],
    brief_report: VerifyReport,
) -> None:
    policy = load_policy(POLICIES / "signed-chain.json")
    report = evaluate_policy(policy, brief, brief_report)
    assert not report.compliant
    by_rule = {check.rule: check for check in report.checks}
    assert not by_rule["require_signed"].ok
    assert not by_rule["chain.require_signed_upstreams"].ok
    assert "unsigned upstream" in by_rule["chain.require_signed_upstreams"].detail
    assert by_rule["chain.max_depth"].ok  # depth 1 ≤ 3


def test_four_eyes_policy_on_an_action_bundle() -> None:
    bundle = json.loads(
        bundle_bytes(
            build_action_bundle(
                "incident",
                "devex",
                "Why did run R-1042 fail, and has this happened before?",
            )
        )
    )
    report = verify_bundle(bundle)
    policy = load_policy(POLICIES / "four-eyes-drafted.json")
    result = evaluate_policy(policy, bundle, report)
    assert result.compliant  # gate recorded, nothing sent, claims re-derive

    # Forge a real send (re-sealed): the policy names it. The bundle itself
    # also fails re-verification — and the exit precedence keeps that verdict.
    from tessera.bundle.format import seal

    tampered = copy.deepcopy(bundle)
    action = tampered["action"]
    assert isinstance(action, dict)
    action["sent"] = True
    tampered = seal({k: v for k, v in tampered.items() if k != "integrity"})
    t_report = verify_bundle(tampered)
    t_result = evaluate_policy(policy, tampered, t_report)
    by_rule = {check.rule: check for check in t_result.checks}
    assert not by_rule["actions.forbid_real_send"].ok
    assert "real send" in by_rule["actions.forbid_real_send"].detail
    assert t_report.exit_code == 2  # the lying bundle keeps its own verdict


def test_read_only_policy_violated_by_an_action_bundle() -> None:
    bundle = json.loads(
        bundle_bytes(
            build_action_bundle(
                "incident",
                "devex",
                "Why did run R-1042 fail, and has this happened before?",
            )
        )
    )
    result = evaluate_policy(
        load_policy(POLICIES / "read-only.json"), bundle, verify_bundle(bundle)
    )
    by_rule = {check.rule: check for check in result.checks}
    assert not by_rule["actions.allow"].ok
    assert "forbids" in by_rule["actions.allow"].detail


def test_allowed_evidence_sources_allowlist(
    brief: dict[str, object], brief_report: VerifyReport
) -> None:
    ok = evaluate_policy(
        _policy({"allowed_evidence_sources": ["bundle:*"]}), brief, brief_report
    )
    assert ok.compliant  # a chain cites only upstream bundles

    bad = evaluate_policy(
        _policy({"allowed_evidence_sources": ["salt_synthetic/*"]}),
        brief,
        brief_report,
    )
    assert not bad.compliant
    assert "outside the allowlist" in bad.checks[0].detail


def test_forbid_unverified_claims_names_the_offender() -> None:
    forged = _load(FORGED)
    report = verify_bundle(forged)
    result = evaluate_policy(
        _policy({"forbid_unverified_claims": True}), forged, report
    )
    assert not result.compliant
    assert "do not re-derive/match" in result.checks[0].detail


def test_allowed_signers_on_an_unsigned_bundle(
    brief: dict[str, object], brief_report: VerifyReport
) -> None:
    result = evaluate_policy(
        _policy({"allowed_signers": ["aa" * 32]}), brief, brief_report
    )
    assert not result.compliant
    assert "unsigned" in result.checks[0].detail


def test_signed_rules_pass_on_a_signed_report(
    brief: dict[str, object], brief_report: VerifyReport
) -> None:
    """The satisfied side of the signer rules, exercised via a synthetic
    report (real key crypto is the signing tests' job, not the policy's)."""
    from dataclasses import replace

    key = "ab" * 32
    signed_report = replace(
        brief_report,
        signature_status="SIGNED",
        signature_public_key=key,
        upstreams=tuple(
            replace(u, signature_status="SIGNED", signer=key)
            for u in brief_report.upstreams
        ),
    )
    result = evaluate_policy(
        _policy(
            {
                "require_signed": True,
                "allowed_signers": [key],
                "chain": {
                    "require_signed_upstreams": True,
                    "allowed_upstream_signers": [key],
                },
            }
        ),
        brief,
        signed_report,
    )
    assert result.compliant, [c.detail for c in result.checks]


def test_chain_rules_fail_closed_when_chain_not_reexecuted(
    brief: dict[str, object],
    brief_report: VerifyReport,
) -> None:
    """A degraded chain (upstreams present, recursion never ran) must not
    vacuously satisfy upstream signer rules."""
    from dataclasses import replace

    degraded = replace(brief_report, upstreams=())
    result = evaluate_policy(
        _policy({"chain": {"require_signed_upstreams": True}}), brief, degraded
    )
    assert not result.compliant
    assert "not re-executed here" in result.checks[0].detail


def test_chain_depth_walks_nesting(brief: dict[str, object]) -> None:
    single = json.loads(
        bundle_bytes(
            build_bundle(
                "business", "Compare Müller Logistik and Nordwind Logistik totals."
            )
        )
    )
    assert chain_depth(single) == 0
    assert chain_depth(brief) == 1
    result = evaluate_policy(
        _policy({"chain": {"max_depth": 0}}), brief, verify_bundle(brief)
    )
    assert not result.compliant
    assert "depth 1 (limit 0)" in result.checks[0].detail


# --- CLI + exit precedence --------------------------------------------------------


def test_cli_exit_precedence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Compliant → the verify exit (0).
    assert verify_main([str(BRIEF), "--policy", str(POLICIES / "read-only.json")]) == 0
    # Non-compliant sound bundle → 5.
    assert (
        verify_main([str(BRIEF), "--policy", str(POLICIES / "signed-chain.json")]) == 5
    )
    # A lying bundle keeps its own verdict (2) even with a violated policy.
    assert verify_main([str(FORGED), "--policy", str(POLICIES / "read-only.json")]) == 2
    capsys.readouterr()
    # An unusable policy on a sound bundle → 5, named on stderr.
    bad = tmp_path / "typo.json"
    bad.write_text(json.dumps(_policy({"require_signd": True})))
    assert verify_main([str(BRIEF), "--policy", str(bad)]) == 5
    assert "unknown rule" in capsys.readouterr().err


def test_cli_json_carries_both_reports(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        verify_main(
            [str(BRIEF), "--json", "--policy", str(POLICIES / "signed-chain.json")]
        )
        == 5
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["verify"]["verdict"] == "PASS"
    assert payload["policy"]["compliant"] is False
    assert payload["policy"]["policy_digest"].startswith("sha256:")
    assert payload["policy"]["scope"] == SCOPE_LINE


def test_policy_digest_is_stable() -> None:
    policy = load_policy(POLICIES / "read-only.json")
    brief = _load(BRIEF)
    report = verify_bundle(brief)
    first = evaluate_policy(policy, brief, report).policy_digest
    second = evaluate_policy(policy, brief, report).policy_digest
    assert first == second


def test_policy_path_is_stdlib_only() -> None:
    """The policy surface must not pull an optional extra (the leak-guard)."""
    script = (
        "import sys\n"
        "import tessera.bundle.policy\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'nacl', 'numpy'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'policy pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
