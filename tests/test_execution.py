"""Tests for the execution layer (Milestone 14 Unit 2, spec 0099).

These pin the execution contract ADR 0025 records: nothing executes over ungrounded
ground (the M13 ``all_grounded`` gate); the simulated default sends nothing and is
transparently marked; the opt-in real :class:`GithubActuator` sends *iff* approved and
credentialed (``sent=True`` is earned), against an injected fake transport — the real
network is never touched; and the receipt is a lossless, JSON-serializable record.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field

import pytest

from tessera.agent.execution import (
    ExecutionReceipt,
    GithubActuator,
    SimulatedActuator,
    execute_action,
    execute_payload,
)
from tessera.agent.payloads import PayloadSlot, RenderedPayload, preview_payload

# A grounded incident question and a grounded PR-summary question (both render).
_INCIDENT = ("incident", "devex", "Why did run R-1042 fail, and has this happened?")
_PR_SUMMARY = ("pr_summary", "devex", "What does PR-201 change?")


@dataclass
class FakeTransport:
    """A recording HTTP stand-in — the real network is never touched in tests or CI."""

    status: int = 201
    response: dict[str, object] = field(
        default_factory=lambda: {"number": 7, "html_url": "https://example/issues/7"}
    )
    calls: list[tuple[str, dict[str, str], dict[str, object]]] = field(
        default_factory=list
    )

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        self.calls.append((url, headers, body))
        return self.status, self.response


# --- the simulated default: a grounded, lossless, side-effect-free receipt ----


@pytest.mark.parametrize("case", [_INCIDENT, _PR_SUMMARY])
def test_simulated_execution_is_grounded_lossless_and_sends_nothing(
    case: tuple[str, str, str],
) -> None:
    """The default actuator records the exact request that would be sent (lossless wrt
    the M13 payload) and sends nothing — grounded, transparently simulated."""
    action, domain, question = case
    receipt = execute_action(action, domain, question)
    payload = preview_payload(action, domain, question)

    assert receipt.executed and receipt.simulated
    assert receipt.sent is False and receipt.withheld is False
    assert receipt.actuator == "simulated"
    assert receipt.outcome == "simulated"
    assert receipt.payload_grounded and receipt.all_grounded
    assert receipt.requires_approval is True

    # Lossless: the receipt's request and slots are exactly the rendered payload's.
    assert (receipt.method, receipt.path, receipt.body) == (
        payload.method,
        payload.path,
        payload.body,
    )
    assert receipt.slots == payload.slots
    assert receipt.slots and all(s.verified for s in receipt.slots)


def test_explicit_simulated_actuator_matches_the_default() -> None:
    """Passing ``SimulatedActuator()`` explicitly is identical to the default — the
    default actuator is the simulated one."""
    explicit = execute_payload(
        preview_payload(*_INCIDENT), actuator=SimulatedActuator()
    )
    default = execute_action(*_INCIDENT)
    assert explicit.to_dict() == default.to_dict()


def test_simulated_result_is_transparently_synthetic_not_a_real_side_effect() -> None:
    """A simulation must never be dressed as a real execution: the result is marked
    simulated and carries no fabricated resource id (issue number / html_url)."""
    receipt = execute_action(*_INCIDENT)
    assert receipt.result.get("simulated") is True
    blob = json.dumps(receipt.result).lower()
    assert "html_url" not in blob and "number" not in blob


# --- the ungrounded gate: nothing executes over ungrounded ground -------------


def test_withheld_action_carries_no_request_and_nothing_sent() -> None:
    """A refused / incompatible / wrong-domain / unknown-run action never yields a
    request: the receipt is withheld, nothing executed or sent."""
    cases = [
        ("incident", "devex", "What does PR-201 change?"),  # incompatible route
        ("incident", "devex", "Why did run R-9999 fail?"),  # unknown run
        ("incident", "devex", "What is the capital of France?"),  # out of scope
        ("pr_summary", "github_actions", "What does PR-201 change?"),  # wrong domain
    ]
    for action, domain, question in cases:
        receipt = execute_action(action, domain, question)
        tag = f"{action}/{domain}: {question}"
        assert receipt.withheld and not receipt.executed, tag
        assert receipt.sent is False and receipt.simulated is False, tag
        assert not receipt.all_grounded and not receipt.payload_grounded, tag
        assert receipt.outcome == "withheld", tag
        assert receipt.withheld_reason, tag
        assert (receipt.method, receipt.path, receipt.body) == ("", "", {}), tag
        assert receipt.slots == (), tag


def _ungrounded_payload() -> RenderedPayload:
    """A hand-built payload with one unverified slot — ``all_grounded`` is False, so
    the gate must withhold it (the provably-failable arm of the gate)."""
    slot = PayloadSlot(
        part="body",
        role="log",
        label="Error log",
        value="x",
        verified=False,
        support=(),
    )
    return RenderedPayload(
        kind="incident",
        domain="devex",
        question="synthetic",
        target="github",
        method="POST",
        path="/repos/{owner}/{repo}/issues",
        body={"title": "t", "body": "b", "labels": ["incident"]},
        slots=(slot,),
        rendered=True,
        withheld_reason=None,
    )


def test_ungrounded_payload_is_withheld_even_from_a_real_approved_actuator() -> None:
    """The gate is in ``execute_payload``, before any actuator: an ungrounded payload
    is withheld even with a real actuator, approval, and a credential — the real
    transport is never called."""
    fake = FakeTransport()
    actuator = GithubActuator(owner="o", repo="r", token="t", transport=fake)
    receipt = execute_payload(_ungrounded_payload(), actuator=actuator, approve=True)
    assert receipt.withheld and not receipt.sent
    assert receipt.outcome == "withheld"
    assert fake.calls == []  # nothing left the system


# --- the opt-in real path: sent is earned (approved AND credentialed) ----------


def test_real_actuator_does_not_send_without_approval() -> None:
    fake = FakeTransport()
    actuator = GithubActuator(owner="o", repo="r", token="t", transport=fake)
    receipt = execute_action(*_INCIDENT, actuator=actuator, approve=False)
    assert receipt.sent is False and not receipt.executed
    assert receipt.outcome == "blocked"
    assert fake.calls == []


def test_real_actuator_does_not_send_without_a_credential() -> None:
    fake = FakeTransport()
    actuator = GithubActuator(owner="o", repo="r", token=None, transport=fake)
    receipt = execute_action(*_INCIDENT, actuator=actuator, approve=True)
    assert receipt.sent is False and not receipt.executed
    assert receipt.outcome == "blocked"
    assert fake.calls == []


def test_real_actuator_sends_iff_approved_and_credentialed() -> None:
    """Approved + credentialed on a grounded payload: exactly one POST, to the
    owner/repo-bound path with no placeholders left, and ``sent=True`` is earned."""
    fake = FakeTransport()
    actuator = GithubActuator(owner="acme", repo="widgets", token="t", transport=fake)
    receipt = execute_action(*_INCIDENT, actuator=actuator, approve=True)

    assert receipt.sent and receipt.executed and not receipt.simulated
    assert receipt.actuator == "github" and receipt.outcome == "created"
    assert receipt.all_grounded
    assert receipt.result.get("status") == 201

    assert len(fake.calls) == 1
    url, headers, body = fake.calls[0]
    assert url == "https://api.github.com/repos/acme/widgets/issues"
    assert "{owner}" not in url and "{repo}" not in url
    assert headers["Authorization"] == "Bearer t"
    # The bound path is recorded on the receipt; the wire body is the payload body.
    assert receipt.path == "/repos/acme/widgets/issues"
    assert body == preview_payload(*_INCIDENT).body


def test_real_actuator_binds_owner_repo_but_keeps_the_grounded_pr_segment() -> None:
    """For a PR comment the ``{pr}`` segment is already bound by the renderer from a
    grounded record; the real actuator binds only ``{owner}``/``{repo}``."""
    fake = FakeTransport(status=201, response={"id": 1})
    actuator = GithubActuator(owner="acme", repo="widgets", token="t", transport=fake)
    receipt = execute_action(*_PR_SUMMARY, actuator=actuator, approve=True)
    assert receipt.sent
    (url, _headers, _body) = fake.calls[0]
    assert url == "https://api.github.com/repos/acme/widgets/issues/PR-201/comments"


def test_real_actuator_non_2xx_is_an_error_not_a_send() -> None:
    fake = FakeTransport(status=422, response={"message": "Validation Failed"})
    actuator = GithubActuator(owner="o", repo="r", token="t", transport=fake)
    receipt = execute_action(*_INCIDENT, actuator=actuator, approve=True)
    assert receipt.sent is False and receipt.outcome == "error"
    assert not receipt.executed
    assert receipt.result.get("status") == 422


# --- receipt self-consistency (adversarial-review regressions) ----------------


def test_blocked_and_error_receipts_are_not_withheld_and_carry_reason_in_result() -> (
    None
):
    """A blocked / errored real send is NOT a withheld action (the request WAS
    grounded): ``withheld`` is False and ``withheld_reason`` is None (reserved for the
    ungrounded trust gate); the detail lives in ``outcome`` + ``result``."""
    blocked = execute_action(
        *_INCIDENT,
        actuator=GithubActuator(
            owner="o", repo="r", token="t", transport=FakeTransport()
        ),
        approve=False,
    )
    assert blocked.outcome == "blocked"
    assert blocked.withheld is False and blocked.withheld_reason is None
    assert blocked.result.get("reason")

    error = execute_action(
        *_INCIDENT,
        actuator=GithubActuator(
            owner="o",
            repo="r",
            token="t",
            transport=FakeTransport(status=422, response={"message": "nope"}),
        ),
        approve=True,
    )
    assert error.outcome == "error"
    assert error.withheld is False and error.withheld_reason is None
    assert error.result.get("reason")


def test_withheld_receipt_reserves_withheld_reason_for_the_ungrounded_gate() -> None:
    """The withheld (ungrounded-gate) receipt carries ``withheld_reason``."""
    receipt = execute_action("incident", "devex", "What does PR-201 change?")
    assert receipt.withheld is True and receipt.withheld_reason


def test_receipt_does_not_alias_the_source_payload_body() -> None:
    """Two receipts from the SAME payload object hold independent ``body`` dicts — a
    trust record never shares mutable state with the payload or another receipt."""
    payload = preview_payload(*_INCIDENT)
    a = execute_payload(payload)
    b = execute_payload(payload)
    assert a.body == b.body == payload.body  # value-equal (lossless)
    assert a.body is not b.body and a.body is not payload.body  # but not shared
    a.body["__injected__"] = "x"
    assert "__injected__" not in b.body and "__injected__" not in payload.body


# --- the simulated path opens no socket ---------------------------------------


def test_simulated_path_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """With ``urlopen`` patched to raise, the default (simulated) execution still
    succeeds — proof the simulated path performs no network I/O."""

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the simulated path must not open a socket")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    receipt = execute_action(*_INCIDENT)  # default SimulatedActuator
    assert receipt.simulated and receipt.sent is False


# --- serialization, errors, determinism ---------------------------------------


def test_receipt_round_trips_through_json() -> None:
    for receipt in (execute_action(*_INCIDENT), execute_action(*_PR_SUMMARY)):
        payload = receipt.to_dict()
        assert json.loads(json.dumps(payload)) == payload
        request = payload["request"]
        assert isinstance(request, dict)
        assert request["method"] == receipt.method
        assert payload["all_grounded"] is True
        assert payload["sent"] is False


def test_unknown_action_raises() -> None:
    with pytest.raises(ValueError, match="unknown action"):
        execute_action("deploy", "devex", "anything")


def test_all_grounded_is_provably_failable() -> None:
    """A receipt whose slot is unverified reads ``all_grounded=False`` — the property
    is not a rubber stamp."""
    bad = ExecutionReceipt(
        kind="incident",
        domain="devex",
        question="q",
        target="github",
        method="POST",
        path="/x",
        body={},
        slots=(
            PayloadSlot(
                part="body",
                role="log",
                label="L",
                value="v",
                verified=False,
                support=(),
            ),
        ),
        actuator="simulated",
        payload_grounded=True,
        executed=True,
        simulated=True,
        sent=False,
        withheld=False,
        withheld_reason=None,
        outcome="simulated",
    )
    assert bad.all_grounded is False


def test_simulated_execution_is_deterministic_across_hash_seeds() -> None:
    """The serialized receipt is byte-stable regardless of PYTHONHASHSEED (the payload
    slots' co-supporting records are sorted at the M11 boundary)."""
    code = (
        "import json; from tessera.agent.execution import execute_action;"
        "print(json.dumps(execute_action('incident','devex',"
        "'Why did run R-1042 fail?').to_dict(), sort_keys=True))"
    )

    def run(seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    assert run("0") == run("1") == run("2026")
