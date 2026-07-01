"""Effectful execution behind approval — a simulated default, an opt-in real seam.

Milestone 14 (specs 0098/0099, ADR 0025). Through thirteen milestones the trust
substrate produced grounded *answers* (M11, :mod:`tessera.agent.grounded`), grounded
*action drafts* (M12, :mod:`tessera.agent.actions`), and the *exact wire request* a
grounded action would send (M13, :mod:`tessera.agent.payloads`) — but stopped at the
wire: M13's :class:`~tessera.agent.payloads.RenderedPayload` renders the request and
**sends nothing** (``sent=False``; ``{owner}``/``{repo}`` unbound). An agent that had
to *act* still took that request and sent it itself, outside Tessera's guarantee.

This layer takes the last step honestly: it **executes** a grounded action through an
:class:`Actuator`, with a **simulated default** that produces a receipt and sends
nothing (the CI-verifiable core) and an **opt-in real** :class:`GithubActuator` behind
a credential + approval. It is a strict *consumer* of the M13 boundary: it renders no
request a second way and invents nothing. The gate that makes execution a trust
*extension* rather than a new write surface is the M13 payload itself:

1. **Nothing executes over ungrounded ground.** :func:`execute_action` renders the M13
   payload and, unless it is ``all_grounded``, returns a **withheld**
   :class:`ExecutionReceipt` — no request, nothing sent. An
   actuator is *never handed an ungrounded payload*. This is the execution-level
   analogue of M11's "a refusal never becomes an answer," M12's "a refusal is carried,
   never drafted over," and M13's "a payload is never rendered over ungrounded ground."
2. **The default sends nothing; the real path is double-gated and earned.**
   :class:`SimulatedActuator` (the default everywhere the repo runs) records the exact
   request that *would* be sent and a transparently-synthetic result — ``sent=False``,
   ``simulated=True``, no fabricated resource id. :class:`GithubActuator` refuses to
   send unless ``approved=True`` **and** it holds a credential, so ``sent=True`` is
   *earned*, never a rubber stamp (a provably-failable check).
3. **The receipt is a lossless trust record.** :class:`ExecutionReceipt` carries the
   gated payload (method, path, body), the grounded slots with their verdicts and
   provenance, the actuator used, the approval, and the outcome — so an agent can audit
   exactly what was (or would be) sent and why it was allowed, without a second
   round-trip.

Deterministic, offline, pure-stdlib on the verifiable core: this module imports only
the payload layer, the grounded-evidence type, and the standard library, so the
leak-guard (``tests/test_agent.py``) still holds — no embedding / LLM / cloud / MCP
import reaches the verifier, and the *simulated* path opens no socket. The real
:class:`GithubActuator` uses only stdlib ``urllib`` (no new dependency, no pip extra —
unlike the ``cloud``/``agent`` extras); its opt-in is a credential + explicit
enablement + approval. It is **never constructed by the default path**, and its **real
HTTP transport and the real network are never invoked in CI** — the actuator itself is
contract-tested in CI against an injected fake transport. Tessera renders and simulates
in this repository; it sends nothing (ADR 0025, the honest edge carried from M13).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from tessera.agent.payloads import PayloadSlot, RenderedPayload, preview_payload

# The synthetic result a simulated execution records — transparently marked, carrying
# no fabricated resource id (issue number, html_url) that could be mistaken for a real
# side effect. A simulation must never be dressed as a real execution (ADR 0025).
_SIMULATED_RESULT: dict[str, object] = {
    "simulated": True,
    "detail": "dry run — no request left Tessera; a human or agent approves and sends.",
}


# --- the execution receipt ----------------------------------------------------


@dataclass(frozen=True)
class ExecutionReceipt:
    """The lossless record of an execution attempt — what was (or would be) sent, the
    provenance of every value in it, which actuator ran, whether it was approved, and
    the outcome.

    ``method``/``path``/``body`` are the request the actuator acted on (empty when the
    action was withheld over ungrounded ground). ``slots`` are the grounded pieces the
    request was assembled from (the M13 payload slots), each with its verdict and
    provenance, so an agent can trace any value without a second round-trip.

    The state is stated plainly in the flags, not inferred: ``withheld`` iff the action
    was not grounded enough to execute (the trust gate fired), and ``withheld_reason``
    carries that gate's reason (``None`` otherwise — a *blocked* or *errored* real send
    is not a withheld action; its detail is in ``outcome`` and ``result``);
    ``simulated`` iff the simulated actuator ran (nothing left the system); ``sent`` iff
    real bytes left Tessera and were accepted (the opt-in real path only, never in CI);
    ``executed``
    means an actuator successfully actuated, really or in simulation (``sent`` or
    ``simulated``). ``requires_approval`` is always true and ``approved`` records
    whether approval was given, preserving the propose-and-approve contract. Read
    :attr:`all_grounded` to tell a grounded execution from a withheld one."""

    kind: str
    domain: str
    question: str
    target: str
    method: str
    path: str
    body: dict[str, object]
    slots: tuple[PayloadSlot, ...]
    actuator: str
    payload_grounded: bool
    executed: bool
    simulated: bool
    sent: bool
    withheld: bool
    withheld_reason: str | None
    outcome: str
    result: dict[str, object] = field(default_factory=dict)
    approved: bool = False
    requires_approval: bool = True
    route_kind: str = ""
    route_reason: str = ""

    @property
    def all_grounded(self) -> bool:
        """True iff this receipt acted on a grounded payload (with slots) whose every
        value passed the boundary verifier — the execution-level faithfulness. Describes
        the *request*, independent of whether it was approved or sent."""
        return (
            self.payload_grounded
            and bool(self.slots)
            and all(s.verified for s in self.slots)
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
            "actuator": self.actuator,
            "payload_grounded": self.payload_grounded,
            "all_grounded": self.all_grounded,
            "executed": self.executed,
            "simulated": self.simulated,
            "sent": self.sent,
            "withheld": self.withheld,
            "withheld_reason": self.withheld_reason,
            "outcome": self.outcome,
            "result": self.result,
            "approved": self.approved,
            "requires_approval": self.requires_approval,
        }


def _receipt(
    payload: RenderedPayload,
    *,
    actuator: str,
    outcome: str,
    executed: bool = False,
    simulated: bool = False,
    sent: bool = False,
    withheld: bool = False,
    withheld_reason: str | None = None,
    result: dict[str, object] | None = None,
    approved: bool = False,
    method: str | None = None,
    path: str | None = None,
    body: dict[str, object] | None = None,
    slots: tuple[PayloadSlot, ...] | None = None,
) -> ExecutionReceipt:
    """An :class:`ExecutionReceipt` sharing the payload's identity and, by default, its
    request + slots; the per-outcome flags are supplied by keyword. The single builder,
    so every actuator records the same shape. ``method``/``path``/``body``/``slots``
    override the payload's (a withheld receipt carries no request; a real ``created``
    receipt carries the bound path)."""
    return ExecutionReceipt(
        kind=payload.kind,
        domain=payload.domain,
        question=payload.question,
        target=payload.target,
        method=payload.method if method is None else method,
        path=payload.path if path is None else path,
        # Copy the inherited request body so a receipt never shares the source payload's
        # mutable dict (``slots`` is an immutable tuple, so it needs no copy).
        body=dict(payload.body) if body is None else body,
        slots=payload.slots if slots is None else slots,
        actuator=actuator,
        payload_grounded=payload.all_grounded,
        executed=executed,
        simulated=simulated,
        sent=sent,
        withheld=withheld,
        withheld_reason=withheld_reason,
        outcome=outcome,
        result={} if result is None else result,
        approved=approved,
        route_kind=payload.route_kind,
        route_reason=payload.route_reason,
    )


# --- the actuator seam --------------------------------------------------------


class Actuator(Protocol):
    """Something that can act on a *grounded* :class:`RenderedPayload`. Implementations
    are only ever handed an :attr:`~RenderedPayload.all_grounded` payload —
    :func:`execute_action` applies the ungrounded gate before dispatch — so an actuator
    never has to decide whether the request is grounded, only whether (and how) to act
    on it."""

    @property
    def name(self) -> str: ...

    def execute(
        self, payload: RenderedPayload, *, approved: bool
    ) -> ExecutionReceipt: ...


@dataclass(frozen=True)
class SimulatedActuator:
    """The default actuator: it records the exact request that *would* be sent and a
    transparently-synthetic result, and sends nothing. No credential, no transport, no
    network — deterministic and safe to run anywhere, including CI and the MCP surface.

    Approval is recorded but not required: a simulation has no side effect, so it needs
    no approval to run; it demonstrates the contract without ever leaving the system."""

    name: str = "simulated"

    def execute(self, payload: RenderedPayload, *, approved: bool) -> ExecutionReceipt:
        return _receipt(
            payload,
            actuator=self.name,
            executed=True,
            simulated=True,
            sent=False,
            outcome="simulated",
            result=dict(_SIMULATED_RESULT),
            approved=approved,
        )


class Transport(Protocol):
    """The HTTP seam the real actuator sends through — injected so the network stays
    out of tests (a fake transport records the call and returns a canned response) and
    out of CI entirely. The default is :class:`_UrllibTransport` (stdlib ``urllib``)."""

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]: ...


@dataclass(frozen=True)
class _UrllibTransport:
    """The real HTTP transport: a JSON ``POST`` via stdlib ``urllib`` (no dependency).
    Constructed only by an opt-in :class:`GithubActuator`; never used in CI."""

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:  # pragma: no cover - real network, never in CI
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(request) as response:
            status = int(response.status)
            payload = response.read().decode("utf-8")
        parsed = json.loads(payload) if payload else {}
        return status, parsed if isinstance(parsed, dict) else {"response": parsed}


@dataclass(frozen=True)
class GithubActuator:
    """The opt-in real actuator: it binds ``{owner}``/``{repo}`` (a deployment binding,
    not evidence) into the grounded request and sends it to GitHub — **iff** it is
    approved and holds a credential. Missing either, it declines and records why
    (``outcome="blocked"``, ``sent=False``), so ``sent=True`` is *earned*, never a
    rubber stamp. A transport error records ``outcome="error"`` and ``sent=False``.

    Pure-stdlib (``urllib``); no new dependency, no pip extra. The opt-in is
    constructing this class with a credential + an explicit ``owner``/``repo`` binding.
    It is **never constructed by the default path**, and its real HTTP transport
    (:class:`_UrllibTransport`) and the real network are **never invoked in CI**:
    Tessera renders and simulates in this repository (ADR 0025). Tests construct it and
    exercise its ``execute`` against an injected fake :class:`Transport`; the real
    network is never touched."""

    owner: str
    repo: str
    token: str | None = None
    base_url: str = "https://api.github.com"
    transport: Transport = field(default_factory=_UrllibTransport)
    name: str = "github"

    def _bind(self, path: str) -> str:
        """Bind the deployment placeholders into the grounded path. ``{pr}`` is already
        bound by the renderer from a grounded record; only ``{owner}``/``{repo}`` (a
        deployment binding) remain."""
        return path.replace("{owner}", self.owner).replace("{repo}", self.repo)

    def execute(self, payload: RenderedPayload, *, approved: bool) -> ExecutionReceipt:
        # A blocked/errored real send is NOT a withheld action (the request WAS
        # grounded); its detail lives in ``outcome`` + ``result``, and
        # ``withheld_reason`` stays None (reserved for the ungrounded gate below).
        if not approved:
            return _receipt(
                payload,
                actuator=self.name,
                outcome="blocked",
                result={
                    "reason": "approval required to send (approve=True not given)."
                },
                approved=False,
            )
        if not self.token:
            return _receipt(
                payload,
                actuator=self.name,
                outcome="blocked",
                result={"reason": "no GitHub credential configured; nothing sent."},
                approved=True,
            )
        url = self.base_url + self._bind(payload.path)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        try:
            status, response = self.transport.post(
                url, headers=headers, body=payload.body
            )
        except (urllib.error.URLError, OSError) as exc:  # pragma: no cover - real net
            return _receipt(
                payload,
                actuator=self.name,
                outcome="error",
                result={"error": f"transport error; nothing created: {exc}"},
                approved=True,
            )
        if not 200 <= status < 300:
            return _receipt(
                payload,
                actuator=self.name,
                outcome="error",
                result={
                    "status": status,
                    "response": response,
                    "reason": f"GitHub returned status {status}; nothing created.",
                },
                approved=True,
            )
        return _receipt(
            payload,
            actuator=self.name,
            path=self._bind(payload.path),
            executed=True,
            simulated=False,
            sent=True,
            outcome="created",
            result={"status": status, "response": response},
            approved=True,
        )


# --- the gated entry points ---------------------------------------------------


def execute_payload(
    payload: RenderedPayload,
    *,
    actuator: Actuator | None = None,
    approve: bool = False,
) -> ExecutionReceipt:
    """Execute a *rendered* payload through ``actuator`` (default:
    :class:`SimulatedActuator`) — or withhold it.

    The single hard precondition is the M13 gate: unless
    :attr:`~RenderedPayload.all_grounded`, this returns a **withheld** receipt with no
    request and nothing sent — an actuator is never handed an ungrounded payload. A
    grounded payload is dispatched to the actuator, which decides whether (and how) to
    act; the simulated default sends nothing."""
    act = actuator if actuator is not None else SimulatedActuator()
    if not payload.all_grounded:
        reason = payload.withheld_reason or (
            "the action is not fully grounded; nothing is executed."
        )
        return _receipt(
            payload,
            actuator=act.name,
            method="",
            path="",
            body={},
            slots=(),
            withheld=True,
            withheld_reason=reason,
            outcome="withheld",
            approved=approve,
        )
    return act.execute(payload, approved=approve)


def execute_action(
    action: str,
    domain: str,
    question: str,
    *,
    actuator: Actuator | None = None,
    approve: bool = False,
) -> ExecutionReceipt:
    """Render a grounded action's dry-run GitHub payload (the M13 boundary) and execute
    it through ``actuator`` (default: :class:`SimulatedActuator`, which sends nothing) —
    or carry a withheld receipt when the action is not fully grounded.

    The convenience entry the MCP ``execute_action`` tool transports (with the simulated
    actuator only; the server holds no credential). Real execution is an explicit,
    credentialed, approval-gated opt-in via a :class:`GithubActuator` on this function —
    never the default and never CI.

    Raises ``ValueError`` for an unknown action kind (propagated from
    :func:`~tessera.agent.actions.draft_action`)."""
    return execute_payload(
        preview_payload(action, domain, question),
        actuator=actuator,
        approve=approve,
    )
