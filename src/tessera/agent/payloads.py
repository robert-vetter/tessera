"""Dry-run executable-payload preview — render the exact request, send nothing.

Milestone 13 (specs 0093/0094, ADR 0024). Through twelve milestones the trust
substrate produced grounded *answers* (M11, :mod:`tessera.agent.grounded`) and
grounded *action drafts* (M12, :mod:`tessera.agent.actions`); both stopped short of
the wire. M12's :class:`~tessera.agent.actions.ActionProposal` records the edge in its
own docstring — it "renders no executable payload." This layer renders it: the **exact
GitHub request** an approver would send for a grounded action — and sends nothing.

It is a strict *consumer* of the M12 boundary. It never reads raw text, never grounds
or drafts a second way, never invents content. It maps a fully-grounded
:class:`~tessera.agent.actions.ActionProposal` into a :class:`RenderedPayload` — the
wire method, path, and JSON body — in which every content value traces to a
verifier-passing field. Three honest properties make it a trust *extension*, not a
write surface:

1. **Every content value is one verified field; the rest is declared scaffolding.**
   The issue ``title`` is the proposal's verified ``title`` field; each body section is
   one verified :class:`~tessera.agent.actions.ActionField` placed under a fixed label;
   the ``{pr}`` path segment of a PR comment is the verified subject field's own cited
   **pull-request** record id. Each :class:`PayloadSlot` carries the value, its
   ``verified`` verdict, and inline provenance. Everything else on the wire is fixed
   *scaffolding*, never asserted grounded: the section headings (:data:`SECTION_LABELS`)
   and code fences, the section separator, the fixed issue ``labels``, and the unbound
   ``{owner}``/``{repo}`` placeholders. The renderer copies content *verbatim* and adds
   nothing — it introduces **no second verifier** (field verification already reduces,
   at the M12 boundary, to claim faithfulness gated at 1.0 plus an "added-nothing"
   check).
2. **Rendered iff ``all_grounded``; otherwise withheld.** A refused, route-
   incompatible, wrong-domain, or partially-verified proposal — or an ``incident``
   with no grounded title (GitHub issues require one) — yields a
   :class:`RenderedPayload` with ``rendered=False`` carrying the reason and **no
   request**. An executable payload is never rendered over ungrounded ground (the
   payload-level analogue of M11's "a refusal never becomes an answer").
3. **Render ≠ send; nothing executed.** The result declares ``sent=False`` /
   ``requires_approval=True``. Tessera builds no transport, opens no socket, holds no
   credential; ``{owner}``/``{repo}`` stay unbound literal placeholders — a deployment
   binding, not evidence. A human or agent binds the target and sends, *outside*
   Tessera (ADR 0024 — the honest edge).

The whole wire request is a pure, deterministic template over the verified field values
plus that fixed scaffolding, so it is *byte-reconstructable* from the proposal's
verified fields alone — a renderer that smuggled an ungrounded token anywhere (the body,
the labels, or the path) fails an independent reconstruction (the provably-failable
"added-nothing" check, Unit 4).

Deterministic, offline, pure-stdlib: this module imports only the action layer and the
grounded-evidence type, so the leak-guard (``tests/test_agent.py``) still holds — no
embedding / LLM / cloud / MCP import reaches the verifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tessera.agent.actions import ActionField, ActionProposal, draft_action
from tessera.agent.grounded import GroundedEvidence

# --- the declared body scaffolding -------------------------------------------
#
# Fixed template vocabulary, declared so the boundary test can prove the rendered
# body adds *nothing* beyond grounded values + this known scaffolding (the
# byte-reconstruction / added-nothing check, Unit 4). Maps a source field role to its
# Markdown section heading; ``_FENCED_ROLES`` wrap the value in a code fence (logs and
# diffs, where verbatim formatting matters and the value may itself contain ``##``).

SECTION_LABELS: dict[str, str] = {
    "title": "Summary",  # used only when the title is a body section (pr_summary)
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
_FENCED_ROLES = frozenset({"log", "code_change"})
_SECTION_SEP = "\n\n"

# The only characters a grounded ``{pr}`` resource id may carry into the URL path —
# one clean segment, no separators, no query/fragment/percent tricks (audit B5).
_RESOURCE_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")


# --- the declared GitHub targets (small, one system) --------------------------


@dataclass(frozen=True)
class _GithubTarget:
    """One GitHub endpoint a grounded action maps to: the wire method and path
    template, whether a (grounded) title is required, and the fixed issue labels.

    The path keeps ``{owner}``/``{repo}`` as unbound literal placeholders (a
    deployment binding, not evidence); ``{pr}`` — present only for the PR-comment
    target — is filled from the verified subject field's cited record id and traced.
    """

    action_kind: str
    method: str
    path: str
    needs_title: bool
    labels: tuple[str, ...]


_TARGETS: dict[str, _GithubTarget] = {
    "incident": _GithubTarget(
        action_kind="incident",
        method="POST",
        path="/repos/{owner}/{repo}/issues",
        needs_title=True,
        labels=("incident",),
    ),
    "pr_summary": _GithubTarget(
        action_kind="pr_summary",
        method="POST",
        path="/repos/{owner}/{repo}/issues/{pr}/comments",
        needs_title=False,
        labels=(),
    ),
}


def available_payload_targets() -> list[dict[str, object]]:
    """The action kinds that can be previewed as a GitHub payload, each with the wire
    method and path template — the discovery surface the MCP tool can transport."""
    return [
        {
            "action": target.action_kind,
            "target": "github",
            "method": target.method,
            "path": target.path,
        }
        for target in _TARGETS.values()
    ]


# --- the serializable rendered payload ----------------------------------------


@dataclass(frozen=True)
class PayloadSlot:
    """One grounded piece of the rendered payload: which wire part it fills
    (``"title"`` | ``"body"`` | ``"path"``), the source field role, the fixed label
    scaffolding it sits under (``""`` for non-body parts), the verbatim grounded
    value, the verifier verdict for that value, and the inline provenance it was drawn
    from. ``verified`` mirrors the source :class:`ActionField` — a slot is built only
    from a verified field, never asserted grounded on trust."""

    part: str
    role: str
    label: str
    value: str
    verified: bool
    support: tuple[GroundedEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "part": self.part,
            "role": self.role,
            "label": self.label,
            "value": self.value,
            "verified": self.verified,
            "support": [e.to_dict() for e in self.support],
        }


@dataclass(frozen=True)
class RenderedPayload:
    """A dry-run executable payload: the exact GitHub request that *would* be sent for
    a grounded action — and the provenance of every value in it — or a withheld result
    carrying why no request was rendered.

    ``method``/``path``/``body`` are the wire request (``body`` is ``{}`` when
    withheld). ``slots`` are the grounded pieces the request was assembled from, each
    with its verdict and provenance, so an agent can trace any value without a second
    round-trip. ``sent``/``requires_approval`` state the render-≠-send contract in the
    payload itself: Tessera renders; a human or agent binds ``{owner}``/``{repo}`` and
    sends; nothing here is executed (ADR 0024). Read :attr:`all_grounded` (not these
    flags) to tell a fully-grounded rendered payload from a withheld one."""

    kind: str
    domain: str
    question: str
    target: str
    method: str
    path: str
    body: dict[str, object]
    slots: tuple[PayloadSlot, ...]
    rendered: bool
    withheld_reason: str | None
    route_kind: str = ""
    route_reason: str = ""
    sent: bool = False
    requires_approval: bool = True

    @property
    def all_grounded(self) -> bool:
        """True iff this is a rendered request (with slots) and *every* slot's value
        passed the boundary verifier — the payload-level faithfulness."""
        return (
            self.rendered and bool(self.slots) and all(s.verified for s in self.slots)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "domain": self.domain,
            "question": self.question,
            "target": self.target,
            "route": {"kind": self.route_kind, "reason": self.route_reason},
            "request": {"method": self.method, "path": self.path, "body": self.body},
            "slots": [s.to_dict() for s in self.slots],
            "rendered": self.rendered,
            "withheld_reason": self.withheld_reason,
            "all_grounded": self.all_grounded,
            "sent": self.sent,
            "requires_approval": self.requires_approval,
        }


# --- rendering ----------------------------------------------------------------


def _fence(value: str) -> str:
    """A backtick fence strictly longer than any backtick run inside ``value``
    (minimum 3). A log or diff line containing ``\\`\\`\\``` could otherwise close the
    fence early and inject markdown — headings, links, fake sections — into the
    rendered (and, on the real path, actually created) issue (audit B4). Still a pure
    function of the value, so the body stays byte-reconstructable."""
    longest = max((len(run) for run in re.findall(r"`+", value)), default=0)
    return "`" * max(3, longest + 1)


def _section(slot: PayloadSlot) -> str:
    """Render one body section: a fixed ``## {label}`` heading over the grounded
    value, code-fenced for logs and diffs (fence length neutralizes any backtick run
    in the value — :func:`_fence`). A pure function of (label, role, value), so the
    assembled body is byte-reconstructable from the verified fields."""
    if slot.role in _FENCED_ROLES:
        fence = _fence(slot.value)
        return f"## {slot.label}\n{fence}\n{slot.value}\n{fence}"
    return f"## {slot.label}\n{slot.value}"


def render_body(slots: tuple[PayloadSlot, ...]) -> str:
    """Assemble the wire body string from the body slots: each section, in order,
    joined by a fixed separator. The single rendering rule — exposed so the boundary
    test can reconstruct the expected body from the verified fields independently."""
    return _SECTION_SEP.join(_section(s) for s in slots if s.part == "body")


def _withheld(
    proposal: ActionProposal, target_name: str, reason: str
) -> RenderedPayload:
    return RenderedPayload(
        kind=proposal.kind,
        domain=proposal.domain,
        question=proposal.question,
        target=target_name,
        method="",
        path="",
        body={},
        slots=(),
        rendered=False,
        withheld_reason=reason,
        route_kind=proposal.route_kind,
        route_reason=proposal.route_reason,
    )


def _slot_from_field(part: str, fld: ActionField) -> PayloadSlot:
    """A body slot from one verified action field, under its declared section label.
    A body field's role must be in :data:`SECTION_LABELS` (the caller guarantees it,
    withholding otherwise) — the renderer never invents a heading."""
    return PayloadSlot(
        part=part,
        role=fld.name,
        label=SECTION_LABELS[fld.name] if part == "body" else "",
        value=fld.value,
        verified=fld.verified,
        support=fld.support,
    )


def _resource_slot(subject: ActionField) -> PayloadSlot | None:
    """The ``{pr}`` resource id for a PR comment, taken from the subject field's own
    cited **pull-request** record (the first support id with a ``PR:`` prefix, e.g.
    ``PR:PR-201`` → ``PR-201``) — a grounded identifier, traced. None when the subject
    cites no PR record, or the id is not a clean single path segment (the
    ``[A-Za-z0-9._-]+`` allowlist, never a dots-only segment — audit B5: ``?``/``#``/
    ``..``/percent-encoding must not reach the URL path), so a comment is never
    addressed to an unbacked or malformed resource (the payload is withheld)."""
    pr = next((e for e in subject.support if e.id.startswith("PR:")), None)
    if pr is None:
        return None
    resource = pr.id.removeprefix("PR:")
    if not _RESOURCE_SEGMENT.fullmatch(resource) or set(resource) <= {"."}:
        return None
    return PayloadSlot(
        part="path",
        role="resource",
        label="",
        value=resource,
        verified=subject.verified,
        support=(pr,),
    )


def render_payload(proposal: ActionProposal) -> RenderedPayload:
    """Render the exact GitHub request for a grounded action proposal — or withhold it.

    Rendered **iff** ``proposal.all_grounded`` (and, for an ``incident``, a grounded
    title exists); otherwise a withheld :class:`RenderedPayload` carries the reason and
    no request. The request is built strictly from the proposal's verified fields:
    every value is copied verbatim, the body is a deterministic template over those
    values, and nothing is sent (ADR 0024)."""
    target = _TARGETS.get(proposal.kind)
    if target is None:
        return _withheld(
            proposal, "github", f"no GitHub payload target for action '{proposal.kind}'"
        )
    if not proposal.all_grounded:
        reason = proposal.refusal or (
            "the action proposal is not fully grounded "
            "(an unverified field); no payload is rendered."
        )
        return _withheld(proposal, "github", reason)

    title_field = next((f for f in proposal.fields if f.name == "title"), None)
    if target.needs_title and title_field is None:
        return _withheld(
            proposal,
            "github",
            "no grounded title is available for a GitHub issue; none rendered.",
        )

    # The fields that become body sections (the title is the issue title for an
    # incident, a body section for a PR comment). Every body field's role must have a
    # declared label; an undeclared role would mean inventing scaffolding, so withhold.
    body_fields = (
        [f for f in proposal.fields if f.name != "title"]
        if proposal.kind == "incident"
        else list(proposal.fields)
    )
    unmapped = sorted({f.name for f in body_fields if f.name not in SECTION_LABELS})
    if unmapped:
        return _withheld(
            proposal,
            "github",
            f"no declared section label for field role(s) {', '.join(unmapped)}; "
            "none rendered.",
        )

    slots: list[PayloadSlot] = []
    body: dict[str, object] = {}
    path = target.path

    if proposal.kind == "incident":
        # title → the issue title (its own wire field); the rest → body sections.
        assert title_field is not None  # guaranteed by needs_title check above
        slots.append(_slot_from_field("title", title_field))
        slots.extend(_slot_from_field("body", f) for f in body_fields)
        body["title"] = title_field.value
        body["body"] = render_body(tuple(slots))
        body["labels"] = list(target.labels)
    else:  # pr_summary → a PR comment; the title is the comment's lead section.
        # Address the comment by the subject's PR record, selected by role (not
        # position: a lifted title field precedes the subject in proposal.fields).
        subject = next((f for f in proposal.fields if f.name == "pull_request"), None)
        resource = _resource_slot(subject) if subject is not None else None
        if resource is None:
            return _withheld(
                proposal,
                "github",
                "no grounded PR resource id to address the comment; none rendered.",
            )
        path = path.replace("{pr}", resource.value)
        slots.append(resource)
        slots.extend(_slot_from_field("body", f) for f in body_fields)
        body["body"] = render_body(tuple(slots))

    return RenderedPayload(
        kind=proposal.kind,
        domain=proposal.domain,
        question=proposal.question,
        target="github",
        method=target.method,
        path=path,
        body=body,
        slots=tuple(slots),
        rendered=True,
        withheld_reason=None,
        route_kind=proposal.route_kind,
        route_reason=proposal.route_reason,
    )


def preview_payload(action: str, domain: str, question: str) -> RenderedPayload:
    """Draft a grounded action and render its dry-run GitHub payload — the convenience
    entry the MCP ``preview_payload`` tool transports. Drafts via
    :func:`~tessera.agent.actions.draft_action` (the M12 boundary), then renders; a
    refused or partially-grounded draft yields a withheld payload, never a request.

    Raises ``ValueError`` for an unknown action kind (a programming error, propagated
    from :func:`draft_action`)."""
    return render_payload(draft_action(action, domain, question))
