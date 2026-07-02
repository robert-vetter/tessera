"""Tests for the dry-run payload renderer (Milestone 13 Unit 2, spec 0094).

These pin the trust contract the MCP ``preview_payload`` tool (Unit 3) transports and
the data-derived boundary measurement (Unit 4) gates: a payload is rendered **iff** the
proposal is fully grounded; every content value is one verified field (lossless); the
body **adds nothing** beyond the verified values and the declared scaffolding
(byte-reconstruction, provably failable); ``{owner}``/``{repo}`` stay unbound and
nothing is sent. The withheld paths (refusal, wrong domain, incompatible route, an
unverified field, a no-title incident) are pinned too — an executable payload is never
rendered over ungrounded ground.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

from tessera.agent.actions import ActionField, ActionProposal, draft_action
from tessera.agent.grounded import GroundedEvidence
from tessera.agent.payloads import (
    available_payload_targets,
    preview_payload,
    render_payload,
)

# Representative, fully-grounded cases (verified above to render with a title).
_INCIDENT_Q = "Why did run R-1042 fail, and has this happened before?"
_PR_Q = "What does PR-201 change?"

# An INDEPENDENT copy of the renderer's declared body scaffolding. The test rebuilds
# the expected wire request from the proposal's verified field VALUES alone, so any
# token the renderer added beyond grounded values + this declared scaffolding makes the
# rebuild differ — the provably-failable 'added-nothing' check (positive reconstruction
# equality, not a subtractive heuristic: no blanket fence-stripping, no first-occurrence
# removal, and it covers the body, the labels, AND the path).
_EXPECTED_LABELS = {
    "title": "Summary",
    "failing_run": "Failing run",
    "log": "Error log",
    "prior_occurrence": "Prior occurrence",
    "documented_incident": "Documented incident",
    "referenced_ticket": "Referenced ticket",
    "resolving_change": "Resolved by",
    "referenced_pull_request": "Pull request",
    "pull_request": "Pull request",
    "code_change": "Code change",
    "motivating_ticket": "Motivating ticket",
}
_EXPECTED_FENCED = {"log", "code_change"}


def _expected_fence(value: str) -> str:
    # Independent copy of the declared fence rule (audit B4): strictly longer than any
    # backtick run inside the value, minimum 3 — so content can never close the fence.
    longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
    return "`" * max(3, longest + 1)


def _expected_section(fld: ActionField) -> str:
    label = _EXPECTED_LABELS[fld.name]
    if fld.name in _EXPECTED_FENCED:
        fence = _expected_fence(fld.value)
        return f"## {label}\n{fence}\n{fld.value}\n{fence}"
    return f"## {label}\n{fld.value}"


def _expected_request(
    proposal: ActionProposal,
) -> tuple[str, str, dict[str, object]]:
    """Rebuild the exact wire (method, path, body) from the proposal's verified fields
    + the declared scaffolding, independently of the renderer's own assembly."""
    if proposal.kind == "incident":
        title = next(f for f in proposal.fields if f.name == "title").value
        sections = [_expected_section(f) for f in proposal.fields if f.name != "title"]
        body: dict[str, object] = {
            "title": title,
            "body": "\n\n".join(sections),
            "labels": ["incident"],
        }
        return "POST", "/repos/{owner}/{repo}/issues", body
    pr_field = next(f for f in proposal.fields if f.name == "pull_request")
    pr = next(e.id for e in pr_field.support if e.id.startswith("PR:")).removeprefix(
        "PR:"
    )
    sections = [_expected_section(f) for f in proposal.fields]
    return (
        "POST",
        f"/repos/{{owner}}/{{repo}}/issues/{pr}/comments",
        {"body": "\n\n".join(sections)},
    )


def _evidence(rec_id: str = "X:1", text: str = "hello world") -> GroundedEvidence:
    return GroundedEvidence(
        id=rec_id,
        source="s",
        locator_kind="table-row",
        locator_parts=(),
        ingested_at="t",
        text=text,
    )


# --- the rendered shapes ------------------------------------------------------


def test_incident_renders_a_github_create_issue() -> None:
    payload = preview_payload("incident", "devex", _INCIDENT_Q)
    assert payload.rendered and payload.all_grounded
    assert payload.target == "github"
    assert payload.method == "POST"
    assert payload.path == "/repos/{owner}/{repo}/issues"
    # title from the verified title field; fixed labels are scaffolding, not evidence.
    title_field = next(f for f in payload.slots if f.role == "title")
    assert payload.body["title"] == title_field.value
    assert payload.body["labels"] == ["incident"]
    assert isinstance(payload.body["body"], str) and payload.body["body"]


def test_pr_summary_renders_a_github_pr_comment() -> None:
    payload = preview_payload("pr_summary", "devex", _PR_Q)
    assert payload.rendered and payload.all_grounded
    assert payload.method == "POST"
    # {pr} bound to the grounded resource id; {owner}/{repo} stay unbound.
    assert payload.path == "/repos/{owner}/{repo}/issues/PR-201/comments"
    assert "title" not in payload.body  # a comment has only a body
    assert isinstance(payload.body["body"], str) and payload.body["body"]


# --- the trust properties -----------------------------------------------------


@pytest.mark.parametrize(
    ("action", "domain", "question"),
    [("incident", "devex", _INCIDENT_Q), ("pr_summary", "devex", _PR_Q)],
)
def test_every_slot_traces_to_a_verified_field(
    action: str, domain: str, question: str
) -> None:
    """Lossless: every non-path slot is exactly one of the proposal's verified fields
    (same value, same support, same verdict) — the renderer added no value of its own
    and dropped none. The path resource slot is traced to the subject's PR record."""
    proposal = draft_action(action, domain, question)
    payload = render_payload(proposal)
    field_slots = [s for s in payload.slots if s.part in ("title", "body")]
    assert len(field_slots) == len(proposal.fields)
    for slot, fld in zip(field_slots, proposal.fields, strict=True):
        assert slot.value == fld.value
        assert {e.id for e in slot.support} == {e.id for e in fld.support}
        assert slot.verified is fld.verified is True
    # The PR resource id is grounded in the subject field's own cited PR record.
    for resource in (s for s in payload.slots if s.part == "path"):
        assert resource.verified
        assert resource.value in payload.path
        subject = next(f for f in proposal.fields if f.name == "pull_request")
        pr_id = next(
            e.id for e in subject.support if e.id.startswith("PR:")
        ).removeprefix("PR:")
        assert resource.value == pr_id
        assert {e.id for e in resource.support} == {f"PR:{pr_id}"}


@pytest.mark.parametrize(
    ("action", "domain", "question"),
    [("incident", "devex", _INCIDENT_Q), ("pr_summary", "devex", _PR_Q)],
)
def test_wire_request_is_byte_reconstructable(
    action: str, domain: str, question: str
) -> None:
    """The whole wire request (method, path, body incl. labels) is byte-identical to an
    independent rebuild from the verified field values plus the declared scaffolding —
    so the renderer introduced no ungrounded content anywhere."""
    proposal = draft_action(action, domain, question)
    payload = render_payload(proposal)
    method, path, body = _expected_request(proposal)
    assert payload.method == method
    assert payload.path == path
    assert payload.body == body


def test_reconstruction_is_provably_failable() -> None:
    """The equality above is not tautological: a token smuggled into the body, the
    labels, or the path makes the request diverge from the independent rebuild (ADR
    0005 discipline). We show the rebuild would reject each such tamper."""
    proposal = draft_action("incident", "devex", _INCIDENT_Q)
    payload = render_payload(proposal)
    _, _, expected = _expected_request(proposal)
    assert payload.body == expected  # the real payload reconstructs exactly
    smuggled_body = {**expected, "body": f"{expected['body']}\n\nNOTE: deploy hotfix."}
    smuggled_label = {**expected, "labels": ["incident", "urgent"]}
    assert smuggled_body != expected  # an extra body line is caught
    assert smuggled_label != expected  # an extra label is caught
    proposal_pr = draft_action("pr_summary", "devex", _PR_Q)
    _, expected_path, _ = _expected_request(proposal_pr)
    smuggled_path = expected_path.replace("/comments", "/comments/extra")
    assert smuggled_path != expected_path  # a path segment is caught


def test_owner_and_repo_stay_unbound_placeholders() -> None:
    """The target binding is a deployment choice, not evidence — never asserted
    grounded, never bound by the renderer."""
    for action, domain, question in [
        ("incident", "devex", _INCIDENT_Q),
        ("pr_summary", "devex", _PR_Q),
    ]:
        payload = preview_payload(action, domain, question)
        assert "{owner}" in payload.path and "{repo}" in payload.path
        assert all(slot.role != "owner" for slot in payload.slots)


def test_render_is_dry_run_nothing_sent() -> None:
    for action, domain, question in [
        ("incident", "devex", _INCIDENT_Q),
        ("pr_summary", "devex", _PR_Q),
        ("incident", "devex", "Why did run R-1001 fail?"),  # withheld
    ]:
        payload = preview_payload(action, domain, question)
        assert payload.sent is False
        assert payload.requires_approval is True


# --- the withheld paths (never a payload over ungrounded ground) --------------


def test_withheld_for_refused_incompatible_and_wrong_domain() -> None:
    cases = [
        ("incident", "devex", "Why did run R-1001 fail?"),  # a passed run
        ("incident", "devex", "Why did run R-9999 fail?"),  # unknown run
        ("incident", "devex", "What is the capital of France?"),  # out of scope
        ("incident", "devex", "What does PR-201 change?"),  # incompatible route
        ("pr_summary", "github_actions", "What does PR-201 change?"),  # wrong domain
    ]
    for action, domain, question in cases:
        payload = preview_payload(action, domain, question)
        tag = f"{action}/{domain}: {question}"
        assert not payload.rendered, tag
        assert not payload.all_grounded, tag
        assert payload.body == {}, tag
        assert payload.method == "" and payload.path == "", tag
        assert payload.slots == (), tag
        assert payload.withheld_reason, tag


def test_a_partially_verified_proposal_is_withheld() -> None:
    """render-iff-all_grounded: a proposal with even one unverified field renders no
    payload — the renderer never asserts a field grounded on trust."""
    ev = _evidence()
    proposal = ActionProposal(
        kind="incident",
        domain="devex",
        question="q",
        route_kind="rca",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=(
            ActionField("title", "hello world", True, (ev,)),
            ActionField("log", "unverified line", False, (ev,)),  # <- not verified
        ),
    )
    assert not proposal.all_grounded
    payload = render_payload(proposal)
    assert not payload.rendered and payload.body == {}
    assert payload.withheld_reason and "not fully grounded" in payload.withheld_reason


def test_a_no_title_incident_is_withheld() -> None:
    """GitHub issues require a title; an incident with no grounded title is withheld,
    never given a fabricated one."""
    ev = _evidence()
    proposal = ActionProposal(
        kind="incident",
        domain="devex",
        question="q",
        route_kind="rca",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=(ActionField("failing_run", "Run X failed.", True, (ev,)),),
    )
    assert proposal.all_grounded  # every field verified, but no title field
    payload = render_payload(proposal)
    assert not payload.rendered
    assert payload.withheld_reason and "title" in payload.withheld_reason


def test_pr_comment_addresses_the_subjects_pr_record_not_just_support_zero() -> None:
    """Review finding (grounding-seam): the {pr} segment must be the subject's PR
    record, selected by its 'PR:' prefix — not blindly support[0]. A subject whose
    first cited record (support is sorted by id, so 'Ticket:…' sorts first) is a
    non-PR record still addresses the PR; a subject citing no PR record is withheld,
    never addressed to the wrong GitHub object."""
    ev_ticket = _evidence("Ticket:DEVEX-204", "ticket text")
    ev_pr = _evidence("PR:PR-201", "pr text")
    subject = ActionField("pull_request", "pr text", True, (ev_ticket, ev_pr))
    proposal = ActionProposal(
        kind="pr_summary",
        domain="devex",
        question="q",
        route_kind="summary",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=(subject,),
    )
    payload = render_payload(proposal)
    assert payload.rendered
    assert payload.path == "/repos/{owner}/{repo}/issues/PR-201/comments"
    resource = next(s for s in payload.slots if s.part == "path")
    assert {e.id for e in resource.support} == {"PR:PR-201"}  # traced to the PR record

    # A subject citing no PR record is withheld, not addressed to the ticket.
    no_pr = ActionProposal(
        kind="pr_summary",
        domain="devex",
        question="q",
        route_kind="summary",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=(ActionField("pull_request", "t", True, (ev_ticket,)),),
    )
    withheld = render_payload(no_pr)
    assert not withheld.rendered and withheld.path == ""
    assert withheld.withheld_reason and "PR resource" in withheld.withheld_reason


def test_an_undeclared_field_role_is_withheld() -> None:
    """Review finding (anti-smuggle vocabulary): a body field whose role has no declared
    section label is withheld — the renderer never invents a heading, so its scaffolding
    vocabulary stays closed and the added-nothing check has no blind spot."""
    ev = _evidence()
    proposal = ActionProposal(
        kind="incident",
        domain="devex",
        question="q",
        route_kind="rca",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=(
            ActionField("title", "hello world", True, (ev,)),
            ActionField("mystery_role", "some value", True, (ev,)),
        ),
    )
    assert proposal.all_grounded
    payload = render_payload(proposal)
    assert not payload.rendered
    assert payload.withheld_reason and "mystery_role" in payload.withheld_reason


# --- discovery, serialization, determinism ------------------------------------


def test_available_payload_targets() -> None:
    targets = available_payload_targets()
    by_action = {t["action"]: t for t in targets}
    assert set(by_action) == {"incident", "pr_summary"}
    assert by_action["incident"]["path"] == "/repos/{owner}/{repo}/issues"
    assert str(by_action["pr_summary"]["path"]).endswith("/issues/{pr}/comments")
    assert all(t["target"] == "github" and t["method"] == "POST" for t in targets)


def test_unknown_action_raises() -> None:
    with pytest.raises(ValueError, match="unknown action"):
        preview_payload("frobnicate", "devex", _INCIDENT_Q)


@pytest.mark.parametrize(
    ("action", "domain", "question"),
    [
        ("incident", "devex", _INCIDENT_Q),
        ("pr_summary", "devex", _PR_Q),
        ("incident", "devex", "Why did run R-1001 fail?"),  # withheld
    ],
)
def test_to_dict_round_trips_through_json(
    action: str, domain: str, question: str
) -> None:
    payload = preview_payload(action, domain, question).to_dict()
    assert json.loads(json.dumps(payload)) == payload
    assert {"request", "slots", "rendered", "all_grounded", "sent"} <= set(payload)
    request = payload["request"]
    assert isinstance(request, dict)
    assert set(request) == {"method", "path", "body"}


def _pr_proposal(*fields: ActionField) -> ActionProposal:
    return ActionProposal(
        kind="pr_summary",
        domain="devex",
        question="q",
        route_kind="summary",
        route_reason="r",
        grounded=True,
        refused=False,
        refusal=None,
        fields=fields,
    )


def test_fence_injection_from_content_is_neutralized() -> None:
    """Audit B4: a log/diff value containing a backtick fence must not be able to
    close the section's fence and inject markdown (headings, links) into the rendered
    — and, on the real path, actually created — issue. The fence is lengthened past
    any run in the value; the value stays verbatim; reconstruction still matches."""
    subject = ActionField(
        "pull_request", "pr text", True, (_evidence("PR:PR-201", "pr text"),)
    )
    hostile = "- ok line\n```\n## Injected heading\n[click me](https://evil.example)"
    diff = ActionField(
        "code_change", hostile, True, (_evidence("Diff:PR-201#h1", hostile),)
    )
    proposal = _pr_proposal(subject, diff)
    payload = render_payload(proposal)
    assert payload.rendered and payload.all_grounded

    body = payload.body["body"]
    assert isinstance(body, str)
    # The hostile value sits verbatim inside a 4-backtick fence it cannot close —
    # exactly one opening and one closing fence of that length exist.
    assert f"## Code change\n````\n{hostile}\n````" in body
    assert body.count("````") == 2
    # The independent reconstruction (same declared rule) still matches byte-for-byte.
    method, path, expected_body = _expected_request(proposal)
    assert (payload.method, payload.path, payload.body) == (method, path, expected_body)


def test_multiline_value_in_a_non_fenced_role_is_withheld() -> None:
    """Review M2: the fence hardening covers fenced roles only — a multiline value in
    a non-fenced role would enter the markdown body verbatim (headings, links). Such a
    payload is withheld, never rendered."""
    subject = ActionField(
        "pull_request", "pr text", True, (_evidence("PR:PR-201", "pr text"),)
    )
    hostile = "ok first line\n## Injected heading\n[click](https://evil.example)"
    ticket = ActionField(
        "motivating_ticket", hostile, True, (_evidence("Ticket:T-1", hostile),)
    )
    payload = render_payload(_pr_proposal(subject, ticket))
    assert not payload.rendered and payload.body == {}
    assert payload.withheld_reason and "multiline" in payload.withheld_reason
    assert "motivating_ticket" in payload.withheld_reason


@pytest.mark.parametrize(
    "hostile_id",
    [
        "PR:..",  # path traversal segment
        "PR:.",  # self segment
        "PR:PR-1?draft=true",  # query injection
        "PR:PR-1#frag",  # fragment injection
        "PR:%2e%2e",  # percent-encoded traversal
        "PR:PR/201",  # extra path segment
        "PR:PR 201",  # whitespace
        "PR:",  # empty
    ],
)
def test_resource_segment_allowlist_withholds_malformed_ids(hostile_id: str) -> None:
    """Audit B5: the ``{pr}`` segment admits only ``[A-Za-z0-9._-]+`` (and never a
    dots-only segment) — anything else is withheld, never spliced into the URL path."""
    subject = ActionField(
        "pull_request", "pr text", True, (_evidence(hostile_id, "pr text"),)
    )
    payload = render_payload(_pr_proposal(subject))
    assert not payload.rendered and payload.path == ""
    assert payload.withheld_reason


def test_payload_is_deterministic_across_hash_seeds() -> None:
    """The rendered request must be byte-stable regardless of PYTHONHASHSEED (a
    claim's co-supporting records are a set, sorted at the M11 boundary). Subprocesses
    vary the seed."""
    code = (
        "import json; from tessera.agent.payloads import preview_payload;"
        "print(json.dumps(preview_payload('incident','devex',"
        "'Why did run R-1042 fail, and has this happened before?').to_dict(),"
        " sort_keys=True))"
    )

    def run(seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    assert run("0") == run("1") == run("2026")
