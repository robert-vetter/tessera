"""Grounded actions — a propose-and-approve layer over the grounded-tool boundary.

Milestone 12 (specs 0087/0089, ADR 0023). The trust substrate has, through eleven
milestones, only ever produced *answers*. An enterprise agent that must *act* — file
the incident this root-cause analysis describes, draft the summary of this pull
request — composed that action itself, ungrounded, outside Tessera's guarantee. This
layer extends the same substrate to the **action draft**: a structured,
JSON-serializable :class:`ActionProposal` whose **every field traces to a
verifier-passing claim**, or it is not proposed at all.

Three honest properties make this a trust *extension*, not a new write surface:

1. **Drafted only from a verifier-checked**
   :class:`~tessera.agent.grounded.GroundedResult`. A drafter never reads raw text,
   never grounds a second way, and never invents content. Each :class:`ActionField`
   is a *selection* of one grounded claim — its value is that claim's verbatim text,
   or a verbatim *fragment* of the claim's own cited evidence (a title taken from an
   error-signature line). ``verified`` is recomputed here: the source claim must have
   passed the boundary verifier **and** the field value must be faithful to it
   (identical text, or a normalized-containment fragment of its evidence). So a field
   that added a single token its evidence does not support reads ``verified=False`` —
   the check is *provably failable*, not tautological (ADR 0005 discipline).
2. **A refusal — or an incompatible grounding — is carried, never drafted over.** If
   the grounding refused (an RCA on a run that *passed*, an unknown run, an
   out-of-scope question) or routed to a path the action kind cannot use, no fields
   are built: the refusal is carried so an action is never proposed on ungrounded
   ground.
3. **Propose-and-approve only.** A proposal declares ``requires_approval=True`` and
   ``executed=False``; Tessera performs no side effect, calls no external system, and
   renders no executable payload. The agent or a human approves and acts *outside*
   Tessera (ADR 0023 — the honest edge of a read-only trust substrate).

Deterministic, offline, pure-stdlib: this module imports only the grounded-tool layer
and the normalizer, so the leak-guard (``tests/test_agent.py``) still holds — no
embedding / LLM / cloud / MCP import reaches the verifier.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from tessera.agent.grounded import (
    GroundedClaim,
    GroundedEvidence,
    GroundedResult,
    ground,
)
from tessera.resolution import normalize

# Error-signature extraction mirrors the engine's own RCA grammar
# (:mod:`tessera.devex.rca`): the specific failing line — synthetic
# ``ERROR <svc>: <msg>`` or a real runner's ``##[error]<msg>`` — not a generic
# trailer. Used only to lift a grounded *title* from a log field's own evidence;
# when neither shape is present (e.g. a ruff-format failure) no title is fabricated.
_ERROR_LINE = re.compile(r"ERROR \S+: (.+)$", re.MULTILINE)
_GH_ERROR_LINE = re.compile(r"##\[error\](.+)$", re.MULTILINE)
# A quoted phrase — the human title inside a PR metadata row,
# ``PR PR-201: "Add retry with backoff …" by …`` — lifted verbatim as the title.
_QUOTED = re.compile(r'"([^"]+)"')


# --- the serializable proposal ------------------------------------------------


@dataclass(frozen=True)
class ActionField:
    """One field of a proposed action: a role name, a grounded value, the
    verifier verdict for *that field*, and the inline provenance it was drawn
    from. ``verified`` is False unless the value is faithful to a verifier-passing
    source claim — a field is never asserted grounded on trust."""

    name: str
    value: str
    verified: bool
    support: tuple[GroundedEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "value": self.value,
            "verified": self.verified,
            "support": [e.to_dict() for e in self.support],
        }


@dataclass(frozen=True)
class ActionProposal:
    """A drafted action, ready to cross the protocol boundary: the action kind,
    the domain and question it was grounded in, the routing decision, the
    field-grounded fields — and, for an incompatible or refused grounding, the
    refusal carried explicitly so an action is never proposed on ungrounded ground.

    ``requires_approval`` / ``executed`` state the propose-and-approve contract in
    the payload itself: Tessera drafts; a human or agent approves and acts outside
    Tessera; nothing here is executed (ADR 0023)."""

    kind: str
    domain: str
    question: str
    route_kind: str
    route_reason: str
    grounded: bool
    refused: bool
    refusal: str | None
    fields: tuple[ActionField, ...]
    requires_approval: bool = True
    executed: bool = False

    @property
    def all_grounded(self) -> bool:
        """True iff this is a real proposal (grounded, with fields) and *every*
        field passed the boundary verifier — the action-level faithfulness."""
        return (
            self.grounded and bool(self.fields) and all(f.verified for f in self.fields)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "domain": self.domain,
            "question": self.question,
            "route": {"kind": self.route_kind, "reason": self.route_reason},
            "grounded": self.grounded,
            "refused": self.refused,
            "refusal": self.refusal,
            "fields": [f.to_dict() for f in self.fields],
            "all_grounded": self.all_grounded,
            "requires_approval": self.requires_approval,
            "executed": self.executed,
        }


# --- the action catalog (small, declared, read-only) --------------------------

TitleFn = Callable[[Sequence[GroundedClaim]], "tuple[str, GroundedClaim] | None"]


@dataclass(frozen=True)
class _ActionKind:
    """A declared, grounded action: which domains and route it draws from, what
    its subject field is called, and how (optionally) to lift a grounded title."""

    name: str
    description: str
    domains: tuple[str, ...]
    required_route: str
    subject_role: str
    subject_hint: str
    title_of: TitleFn


def _incident_title(
    claims: Sequence[GroundedClaim],
) -> tuple[str, GroundedClaim] | None:
    """The most specific failing line, lifted verbatim from a log claim's evidence
    (so it is grounded by containment). None when no error-shaped line exists."""
    for claim in claims:
        for pattern in (_ERROR_LINE, _GH_ERROR_LINE):
            match = pattern.search(claim.text)
            if match:
                return match.group(1).strip(), claim
    return None


def _pr_title(claims: Sequence[GroundedClaim]) -> tuple[str, GroundedClaim] | None:
    """The PR's human title, lifted verbatim from the quoted phrase in its
    metadata row (the first claim of a change-summary)."""
    if not claims:
        return None
    head = claims[0]
    match = _QUOTED.search(head.text)
    return (match.group(1), head) if match else None


_INCIDENT = _ActionKind(
    name="incident",
    description=(
        "Draft an incident report from a failed pipeline run's root-cause analysis: "
        "the failing run, the error log lines, any prior occurrence and documented "
        "incident, and the resolving change — every field grounded in the cited "
        "evidence. A draft a human/agent approves and files; Tessera files nothing."
    ),
    domains=("devex", "github_actions"),
    required_route="rca",
    subject_role="failing_run",
    subject_hint="a pipeline run (e.g. 'Why did run R-1042 fail?')",
    title_of=_incident_title,
)
_PR_SUMMARY = _ActionKind(
    name="pr_summary",
    description=(
        "Draft a pull-request summary from a change analysis: the PR metadata, the "
        "diff hunks themselves, and the motivating ticket when the PR names one — "
        "every field grounded in the cited evidence. A draft a human/agent approves "
        "and posts; Tessera posts nothing."
    ),
    domains=("devex",),
    required_route="summary",
    subject_role="pull_request",
    subject_hint="a pull request (e.g. 'What does PR-201 change?')",
    title_of=_pr_title,
)

_CATALOG: dict[str, _ActionKind] = {
    _INCIDENT.name: _INCIDENT,
    _PR_SUMMARY.name: _PR_SUMMARY,
}


def available_actions() -> list[dict[str, object]]:
    """The actions an agent can draft, with the domains and route each draws from —
    the discovery surface the MCP ``list_actions`` tool transports (Unit 4)."""
    return [
        {
            "name": kind.name,
            "description": kind.description,
            "domains": list(kind.domains),
            "from_route": kind.required_route,
        }
        for kind in _CATALOG.values()
    ]


def available_action_names() -> tuple[str, ...]:
    return tuple(_CATALOG)


# --- drafting -----------------------------------------------------------------


def _role(text: str) -> str:
    """A non-subject claim's role, read from the engine's own stable claim grammar
    (the markers the verifier itself keys on) — not a fragile internal coupling."""
    if text.startswith("Recurring failure:"):
        return "prior_occurrence"
    if text.startswith("Documented incident:"):
        return "documented_incident"
    if text.startswith("Resolved by:"):
        return "resolving_change"
    if text.startswith("Motivating ticket:"):
        return "motivating_ticket"
    if text.startswith("Ticket "):
        return "referenced_ticket"
    if text.startswith("PR "):
        return "referenced_pull_request"
    if text.startswith(("diff --git", "@@ ")):
        return "code_change"
    return "log"


def _evidence_text(claim: GroundedClaim) -> str:
    return "\n".join(e.text for e in claim.support)


def _field(name: str, value: str, claim: GroundedClaim) -> ActionField:
    """Build a field from one source claim, recomputing groundedness: the source
    claim must have passed the boundary verifier AND the value must be faithful to
    it — its exact text, or a normalized-containment fragment of its own evidence.
    Anything else reads ``verified=False`` (the provably-failable check)."""
    faithful = value == claim.text or (
        bool(normalize(value)) and normalize(value) in normalize(_evidence_text(claim))
    )
    return ActionField(
        name=name,
        value=value,
        verified=claim.verified and faithful,
        support=claim.support,
    )


def _draft_fields(kind: _ActionKind, result: GroundedResult) -> list[ActionField]:
    fields: list[ActionField] = []
    title = kind.title_of(result.claims)
    if title is not None:
        fields.append(_field("title", title[0], title[1]))
    for index, claim in enumerate(result.claims):
        role = kind.subject_role if index == 0 else _role(claim.text)
        fields.append(_field(role, claim.text, claim))
    return fields


def _refused(
    kind: str, domain: str, question: str, result: GroundedResult | None, refusal: str
) -> ActionProposal:
    return ActionProposal(
        kind=kind,
        domain=domain,
        question=question,
        route_kind=result.route_kind if result else "",
        route_reason=result.route_reason if result else "",
        grounded=False,
        refused=True,
        refusal=refusal,
        fields=(),
    )


def draft_action(action_kind: str, domain: str, question: str) -> ActionProposal:
    """Draft a grounded, field-verified, propose-and-approve action — or carry a
    refusal. The action is built strictly from ``ground(domain, question)`` (the
    Milestone-11 boundary): a refused or route-incompatible grounding yields a
    carried refusal with no fields, never a fabricated action (ADR 0023).

    Raises ``ValueError`` for an unknown action kind (a programming error, like an
    unknown domain in :func:`ground`)."""
    if action_kind not in _CATALOG:
        raise ValueError(
            f"unknown action {action_kind!r} — pick one of "
            f"{', '.join(available_action_names())}"
        )
    kind = _CATALOG[action_kind]

    if domain not in kind.domains:
        return _refused(
            action_kind,
            domain,
            question,
            None,
            f"the '{kind.name}' action applies to domain(s) "
            f"{', '.join(kind.domains)}, not '{domain}'.",
        )

    result = ground(domain, question)
    if result.refused:
        # Carry the grounding's own refusal — an action is never proposed on
        # ungrounded ground (a passed/unknown run, an out-of-scope question).
        return _refused(action_kind, domain, question, result, result.refusal or "")
    if result.route_kind != kind.required_route:
        return _refused(
            action_kind,
            domain,
            question,
            result,
            f"cannot draft a '{kind.name}' from this question: it routed to "
            f"'{result.route_kind}', not '{kind.required_route}' — name "
            f"{kind.subject_hint}.",
        )

    return ActionProposal(
        kind=action_kind,
        domain=domain,
        question=question,
        route_kind=result.route_kind,
        route_reason=result.route_reason,
        grounded=True,
        refused=False,
        refusal=None,
        fields=tuple(_draft_fields(kind, result)),
    )
