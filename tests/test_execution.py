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
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import pytest

from tessera.agent.execution import (
    _MAX_PRECHECK_PAGES,
    _PRECHECK_PER_PAGE,
    ExecutionReceipt,
    GithubActuator,
    SimulatedActuator,
    execute_action,
    execute_payload,
    idempotency_key,
    idempotency_marker,
)
from tessera.agent.payloads import PayloadSlot, RenderedPayload, preview_payload

# A grounded incident question and a grounded PR-summary question (both render).
_INCIDENT = ("incident", "devex", "Why did run R-1042 fail, and has this happened?")
_PR_SUMMARY = ("pr_summary", "devex", "What does PR-201 change?")


@dataclass
class FakeTransport:
    """A recording HTTP stand-in — the real network is never touched in tests or CI.

    ``post`` records the create call and returns ``status``/``response``. ``get`` is the
    idempotency pre-check read: it records the URL in ``gets`` and returns the status
    plus ``existing`` (prior issues/comments — empty by default, so nothing pre-exists).
    Set ``existing`` to simulate a prior identical action, ``get_status`` to a non-2xx,
    or ``raise_on_get`` to simulate an inconclusive pre-check."""

    status: int = 201
    response: dict[str, object] = field(
        default_factory=lambda: {"number": 7, "html_url": "https://example/issues/7"}
    )
    calls: list[tuple[str, dict[str, str], dict[str, object]]] = field(
        default_factory=list
    )
    existing: list[dict[str, object]] = field(default_factory=list)
    get_status: int = 200
    raise_on_get: bool = False
    page_size: int = _PRECHECK_PER_PAGE
    always_full: bool = False
    gets: list[str] = field(default_factory=list)

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        self.calls.append((url, headers, body))
        return self.status, self.response

    def get(self, url: str, *, headers: dict[str, str]) -> tuple[int, object]:
        self.gets.append(url)
        if self.raise_on_get:
            raise urllib.error.URLError("simulated pre-check transport error")
        if self.always_full:  # every page is full — simulates an endless thread
            return self.get_status, self.existing
        match = re.search(r"[?&]page=(\d+)", url)
        page = int(match.group(1)) if match else 1
        start = (page - 1) * self.page_size
        return self.get_status, self.existing[start : start + self.page_size]


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
    """Approved + credentialed on a grounded payload: one idempotency pre-check (finding
    nothing) then exactly one POST, to the owner/repo-bound path with no placeholders
    left, and ``sent=True`` is earned."""
    fake = FakeTransport()
    actuator = GithubActuator(owner="acme", repo="widgets", token="t", transport=fake)
    payload = preview_payload(*_INCIDENT)
    key = idempotency_key(payload)
    receipt = execute_action(*_INCIDENT, actuator=actuator, approve=True)

    assert receipt.sent and receipt.executed and not receipt.simulated
    assert receipt.actuator == "github" and receipt.outcome == "created"
    assert receipt.all_grounded
    assert receipt.result.get("status") == 201

    assert len(fake.gets) == 1  # the idempotency pre-check ran and found nothing
    assert len(fake.calls) == 1
    url, headers, body = fake.calls[0]
    assert url == "https://api.github.com/repos/acme/widgets/issues"
    assert "{owner}" not in url and "{repo}" not in url
    assert headers["Authorization"] == "Bearer t"
    assert receipt.path == "/repos/acme/widgets/issues"
    # The wire body is the grounded body PLUS the deployment-scaffolding marker: the
    # grounded content is preserved verbatim, the marker + idem-label are embedded, the
    # receipt records exactly what was sent, and it carries the idempotency key.
    grounded_body = payload.body["body"]
    posted_body = body["body"]
    posted_labels = body["labels"]
    assert isinstance(grounded_body, str) and isinstance(posted_body, str)
    assert isinstance(posted_labels, list)
    assert grounded_body in posted_body
    assert idempotency_marker(key) in posted_body
    assert f"idem-{key.split(':')[1][:16]}" in posted_labels
    assert receipt.body == body
    assert receipt.idempotency_key == key


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


# --- best-effort idempotency on the real path (Milestone 15, ADR 0026) --------


def test_idempotency_dedupes_a_re_run_end_to_end() -> None:
    """The core M15 property: a first approved+credentialed send creates the issue with
    the idempotency marker embedded; a second run against a target that now holds that
    issue finds it via the pre-check and returns ``exists`` — no duplicate POST."""
    first = FakeTransport()
    created = execute_action(
        *_INCIDENT,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=first),
        approve=True,
    )
    assert created.outcome == "created" and created.sent
    posted_body = first.calls[0][2]
    assert isinstance(posted_body["body"], str)

    # The target now contains exactly the issue the first run created (same marker).
    second = FakeTransport(
        existing=[
            {"number": 42, "html_url": "https://x/42", "body": posted_body["body"]}
        ]
    )
    rerun = execute_action(
        *_INCIDENT,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=second),
        approve=True,
    )
    assert rerun.outcome == "exists" and rerun.sent is False and not rerun.executed
    assert second.gets and second.calls == []  # a GET happened; no duplicate POST
    assert rerun.idempotency_key == created.idempotency_key
    existing = rerun.result.get("existing")
    assert isinstance(existing, dict) and existing.get("number") == 42


def test_inconclusive_precheck_refuses_rather_than_duplicates() -> None:
    """When the pre-check cannot decide — a non-2xx list response or a transport error —
    the actuator refuses: ``outcome="inconclusive"``, nothing sent, no POST. A correct
    refusal beats a confident duplicate (groundedness applied to a side effect)."""
    for fake in (
        FakeTransport(get_status=403),  # e.g. a rate-limited list read
        FakeTransport(raise_on_get=True),  # a transport error on the pre-check
    ):
        receipt = execute_action(
            *_INCIDENT,
            actuator=GithubActuator(owner="o", repo="r", token="t", transport=fake),
            approve=True,
        )
        assert receipt.outcome == "inconclusive"
        assert receipt.sent is False and not receipt.executed
        assert receipt.withheld is False and receipt.withheld_reason is None
        assert fake.calls == []  # never created over an undecidable pre-check
        assert receipt.idempotency_key  # the key is still recorded, for audit


def test_precheck_requires_the_exact_marker_not_just_a_label_hit() -> None:
    """A candidate returned by the label-filtered list that does NOT carry the exact
    marker in its body is not trusted — the actuator creates rather than falsely
    deduping on a bare label collision."""
    fake = FakeTransport(
        existing=[{"number": 1, "html_url": "https://x/1", "body": "unrelated issue"}]
    )
    receipt = execute_action(
        *_INCIDENT,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=fake),
        approve=True,
    )
    assert receipt.outcome == "created" and receipt.sent
    assert len(fake.calls) == 1  # the non-matching candidate was correctly ignored


def test_idempotency_key_is_deterministic_and_excludes_the_marker() -> None:
    """The key is a stable ``sha256:`` digest of the grounded request, computed without
    the marker (so it never depends on itself) and identical across calls."""
    payload = preview_payload(*_INCIDENT)
    key = idempotency_key(payload)
    assert key.startswith("sha256:") and len(key) == len("sha256:") + 64
    assert idempotency_key(payload) == key  # deterministic
    # The grounded payload carries no marker/key: the key is a function of the grounded
    # body alone, so embedding the key later cannot change it (it converges).
    assert key not in json.dumps(payload.body)


def test_simulated_and_withheld_receipts_carry_no_idempotency_key() -> None:
    """The idempotency key is a real-path concept: the simulated dry run and the
    ungrounded / blocked gates form no real send and carry ``idempotency_key=None``."""
    simulated = execute_action(*_INCIDENT)
    assert simulated.simulated and simulated.idempotency_key is None
    withheld = execute_action("incident", "devex", "What does PR-201 change?")
    assert withheld.withheld and withheld.idempotency_key is None
    blocked = execute_action(
        *_INCIDENT,
        actuator=GithubActuator(
            owner="o", repo="r", token="t", transport=FakeTransport()
        ),
        approve=False,
    )
    assert blocked.outcome == "blocked" and blocked.idempotency_key is None


def test_pr_comment_idempotency_lists_comments_and_dedupes() -> None:
    """A pr_summary comment carries no label, so its pre-check lists the PR's comments
    and matches the exact marker: a first send creates the comment; a re-run against a
    thread that already contains it returns ``exists`` with no duplicate."""
    first = FakeTransport(status=201, response={"id": 1})
    created = execute_action(
        *_PR_SUMMARY,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=first),
        approve=True,
    )
    assert created.outcome == "created" and created.sent
    posted = first.calls[0][2]
    assert isinstance(posted["body"], str)
    assert first.gets and "/issues/PR-201/comments?" in first.gets[0]

    second = FakeTransport(existing=[{"id": 1, "body": posted["body"]}])
    rerun = execute_action(
        *_PR_SUMMARY,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=second),
        approve=True,
    )
    assert rerun.outcome == "exists" and rerun.sent is False
    assert second.calls == []


def test_idempotency_pre_check_paginates_a_long_comment_thread() -> None:
    """A PR comment lands at the END of the thread, so on a busy PR its marker sits on a
    later page: the pre-check pages through and finds it — no duplicate. (Pins the
    adversarial review's confirmed pagination defect.)"""
    first = FakeTransport(status=201, response={"id": 1})
    created = execute_action(
        *_PR_SUMMARY,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=first),
        approve=True,
    )
    assert created.outcome == "created"
    marker_body = first.calls[0][2]["body"]
    assert isinstance(marker_body, str)

    # A full first page of unrelated comments + Tessera's marker comment on page 2.
    thread: list[dict[str, object]] = [
        {"id": i, "body": f"comment {i}"} for i in range(_PRECHECK_PER_PAGE)
    ] + [{"id": 999, "body": marker_body}]
    second = FakeTransport(existing=thread)
    rerun = execute_action(
        *_PR_SUMMARY,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=second),
        approve=True,
    )
    assert rerun.outcome == "exists" and rerun.sent is False
    assert len(second.gets) == 2  # paged to page 2 to find the marker
    assert second.calls == []  # no duplicate comment


def test_pre_check_refuses_when_it_cannot_scan_the_whole_thread() -> None:
    """A pathologically long thread whose pages never yield the marker: the pre-check
    pages to its cap and then REFUSES (``inconclusive``), never risking a duplicate."""
    endless = FakeTransport(
        existing=[{"id": i, "body": f"c{i}"} for i in range(_PRECHECK_PER_PAGE)],
        always_full=True,
    )
    receipt = execute_action(
        *_PR_SUMMARY,
        actuator=GithubActuator(owner="o", repo="r", token="t", transport=endless),
        approve=True,
    )
    assert receipt.outcome == "inconclusive" and receipt.sent is False
    assert endless.calls == []  # never created despite not finding the marker
    assert len(endless.gets) == _MAX_PRECHECK_PAGES  # capped


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
