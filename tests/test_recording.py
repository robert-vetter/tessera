"""Tests for the real-execution receipt scrubber (Milestone 15 Unit 3, spec 0105).

These pin that :func:`tessera.agent.recording.redact_receipt` produces a committable
receipt: GitHub's echoed response is reduced to the honest allow-list, any token-like
value anywhere is replaced with ``"***"``, the input is never mutated, and the
non-response results (withheld / exists / simulated) pass through unchanged. The
end-to-end case drives the real ``GithubActuator`` against a fake transport returning a
realistic GitHub issue body — the network is never touched.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from tessera.agent.execution import GithubActuator, execute_action
from tessera.agent.recording import redact_receipt

# A grounded incident (a run is named, so it grounds as an incident, not a lookup).
_INCIDENT = ("incident", "devex", "Why did run R-1042 fail?")

# A realistic GitHub create-issue response: the allow-list fields, plus the volatile /
# identifying fields the scrubber must drop, plus a deliberately-planted token-like key.
_GITHUB_ISSUE_RESPONSE: dict[str, object] = {
    "number": 7,
    "html_url": "https://github.com/acme/sandbox/issues/7",
    "state": "open",
    "title": "Incident: pages deploy failed",
    "id": 1234567890,
    "node_id": "I_kwDOABCDEF",
    "url": "https://api.github.com/repos/acme/sandbox/issues/7",
    "repository_url": "https://api.github.com/repos/acme/sandbox",
    "created_at": "2026-07-01T12:00:00Z",
    "user": {
        "login": "octocat",
        "id": 583231,
        "node_id": "MDQ6VXNlcjU4MzIzMQ==",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231",
    },
    "performed_via_github_app_token": "ghs_shouldNeverBeCommitted",
}


@dataclass
class _RecordingTransport:
    """A fake transport: get() finds nothing (the create proceeds), post() returns the
    realistic GitHub issue response above. The real network is never touched."""

    response: dict[str, object] = field(
        default_factory=lambda: dict(_GITHUB_ISSUE_RESPONSE)
    )

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        return 201, self.response

    def get(self, url: str, *, headers: dict[str, str]) -> tuple[int, object]:
        return 200, []


def test_redact_reduces_the_github_response_to_the_allow_list() -> None:
    receipt: dict[str, object] = {
        "outcome": "created",
        "sent": True,
        "result": {"status": 201, "response": dict(_GITHUB_ISSUE_RESPONSE)},
    }
    scrubbed = redact_receipt(receipt)
    response = scrubbed["result"]["response"]  # type: ignore[index]
    assert set(response) == {"number", "html_url", "state", "title"}
    assert response["number"] == 7
    assert response["html_url"] == "https://github.com/acme/sandbox/issues/7"
    # The identifying / volatile fields are gone entirely.
    for dropped in ("id", "node_id", "url", "repository_url", "created_at", "user"):
        assert dropped not in response


def test_redact_replaces_token_like_values_anywhere() -> None:
    receipt: dict[str, object] = {
        "result": {
            "response": {"number": 1, "performed_via_github_app_token": "ghs_secret"},
            "nested": {"api_key": "sk-123", "reason": "kept"},
        },
    }
    scrubbed = redact_receipt(receipt)
    # The token field is dropped by the allow-list; the nested api_key is redacted.
    nested = scrubbed["result"]["nested"]  # type: ignore[index]
    assert nested["api_key"] == "***"
    assert nested["reason"] == "kept"
    # No secret string survives anywhere in the serialized artifact.
    blob = json.dumps(scrubbed)
    assert "ghs_secret" not in blob and "sk-123" not in blob


def test_redact_does_not_mutate_the_input() -> None:
    receipt: dict[str, object] = {"result": {"response": dict(_GITHUB_ISSUE_RESPONSE)}}
    before = json.dumps(receipt, sort_keys=True)
    redact_receipt(receipt)
    assert json.dumps(receipt, sort_keys=True) == before  # input untouched


def test_redact_passes_non_response_results_through() -> None:
    for result in (
        {
            "reason": "an identical grounded action already exists",
            "existing": {"number": 3},
        },
        {
            "reason": "the idempotency pre-check could not decide",
            "detail": {"status": 403},
        },
        {"simulated": True, "detail": "dry run — no request left Tessera"},
    ):
        receipt: dict[str, object] = {"outcome": "x", "result": result}
        assert redact_receipt(receipt)["result"] == result


def test_end_to_end_a_real_send_receipt_scrubs_clean() -> None:
    """Drive the real GithubActuator against a fake transport that echoes a realistic
    GitHub issue response, then scrub the receipt — the committed artifact keeps the
    honest allow-list, embeds the idempotency key, and leaks no secret or identity."""
    actuator = GithubActuator(
        owner="acme", repo="sandbox", token="t", transport=_RecordingTransport()
    )
    receipt = execute_action(*_INCIDENT, actuator=actuator, approve=True)
    assert receipt.sent and receipt.outcome == "created"

    scrubbed = redact_receipt(receipt.to_dict())
    assert scrubbed["sent"] is True
    assert scrubbed["idempotency_key"]  # the key is preserved for audit
    response = scrubbed["result"]["response"]  # type: ignore[index]
    assert set(response) == {"number", "html_url", "state", "title"}
    # Nothing identifying, volatile, or secret survives in the committable receipt.
    blob = json.dumps(scrubbed)
    for leak in ("octocat", "avatar_url", "node_id", "ghs_", "Bearer", '"token"'):
        assert leak not in blob
