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

On the **real path only**, execution is **best-effort idempotent** (Milestone 15, ADR
0026). Before creating, :class:`GithubActuator` derives a deterministic key from the
grounded request (``sha256`` over its canonical ``method``/``path``/``body``, the marker
excluded so the key never depends on itself), stamps it onto the outgoing issue/comment
as a marker — an HTML comment, a human-visible footer, and (for an issue) a
deterministic ``idem-<key>`` label — and **pages** the target's **primary,
immediately-consistent** issues/comments endpoint for that marker. A verified hit
short-circuits to ``outcome="exists"`` (nothing created); a pre-check that cannot decide
(a page read errors or is non-2xx, or the scan hits its page cap) short-circuits to
``outcome="inconclusive"`` (nothing created) — **never a silent duplicate** (a correct
refusal beats a confident duplicate, the groundedness principle applied to a side
effect). It is **best-effort, not exactly-once**: a genuine concurrent create (two sends
before either issue is listable) can still duplicate; the eventually-consistent search
index is deliberately *not* used, so the residual window is that true race, not a
~minute of search lag. The marker is declared deployment scaffolding (like the fixed M13
labels/headings): a deterministic function of already-verified values, asserting no new
claim, and it never enters the M13 renderer or the grounded slots — so **faithfulness
stays 1.0 across every boundary**. The simulated default embeds no marker and does no
pre-check; it records the grounded template unchanged.

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

import hashlib
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
    # The deterministic best-effort-idempotency key of the request, on the real path
    # (``sha256:<hex>``); ``None`` on the simulated dry run and the ungrounded/blocked
    # gates, which form no real send (Milestone 15, ADR 0026).
    idempotency_key: str | None = None
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
            "idempotency_key": self.idempotency_key,
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
    idempotency_key: str | None = None,
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
        idempotency_key=idempotency_key,
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
    out of CI entirely. The default is :class:`_UrllibTransport` (stdlib ``urllib``).

    ``get`` is the read half the idempotency pre-check needs (Milestone 15): it returns
    the parsed JSON, which for the issues/comments list endpoints is a JSON *array*, so
    the payload type is ``object`` (a ``list`` or, for a search-style endpoint, a
    ``dict``) rather than ``post``'s ``dict``."""

    def post(
        self, url: str, *, headers: dict[str, str], body: dict[str, object]
    ) -> tuple[int, dict[str, object]]: ...

    def get(self, url: str, *, headers: dict[str, str]) -> tuple[int, object]: ...


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

    def get(
        self, url: str, *, headers: dict[str, str]
    ) -> tuple[int, object]:  # pragma: no cover - real network, never in CI
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request) as response:
            status = int(response.status)
            payload = response.read().decode("utf-8")
        return status, (json.loads(payload) if payload else [])


# --- best-effort idempotency (real path only, Milestone 15, ADR 0026) ---------

_MARKER_PREFIX = "tessera-idempotency-key"

# The pre-check pages through the primary list endpoint — the repo's issues
# (``state=all``, unfiltered) or a PR's whole comment thread. It is deliberately
# label-independent (audit B2): a dropped, deleted, or never-attached ``idem-`` label
# must not defeat the dedup, so the scan trusts only the exact body marker. The page
# cap bounds the worst case: if the marker is not found within it, the pre-check
# REFUSES (``inconclusive``) rather than risk a duplicate over an un-scanned page.
_PRECHECK_PER_PAGE = 100
_MAX_PRECHECK_PAGES = 20


def _canonical_request(payload: RenderedPayload) -> bytes:
    """The canonical bytes the idempotency key hashes: the grounded request's method,
    (unbound) path, and body — deployment-independent (``{owner}``/``{repo}`` still
    unbound), so the same grounded action has one key regardless of target; per-repo
    dedup comes from querying *within* the target repo. Sorted keys + fixed separators
    make it byte-stable across processes and ``PYTHONHASHSEED``."""
    return json.dumps(
        {"method": payload.method, "path": payload.path, "body": payload.body},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def idempotency_key(payload: RenderedPayload) -> str:
    """The deterministic best-effort-idempotency key of a grounded request
    (``"sha256:<hex>"``). A pure function of the grounded ``method``/``path``/``body``,
    computed *without* the marker so the key never depends on itself."""
    return "sha256:" + hashlib.sha256(_canonical_request(payload)).hexdigest()


def idempotency_marker(key: str) -> str:
    """The exact, machine-findable marker embedded in the issue/comment body — an HTML
    comment (invisible when the Markdown renders) carrying the key. The pre-check
    verifies this exact substring in a candidate's body before trusting it, so a label
    collision alone can never be mistaken for a match."""
    return f"<!-- {_MARKER_PREFIX}: {key} -->"


def _idempotency_label(key: str) -> str:
    """A short, deterministic label handle for the key — a *visible* marker on the
    created issue for humans and dashboards. Deliberately **not load-bearing** for the
    pre-check (audit B2): the dedup scan is label-independent and trusts only the exact
    body marker, so a label GitHub drops or a user deletes cannot cause a duplicate.
    Issues only; a comment carries no label."""
    digest = key.split(":", 1)[1]
    return f"idem-{digest[:16]}"


def _embed_idempotency(body: dict[str, object], key: str) -> dict[str, object]:
    """Return a *copy* of the request body with the idempotency marker embedded — a
    footer (HTML comment + a human-visible line) appended to ``body`` and, for an issue,
    the ``idem-`` label appended to ``labels``. Declared scaffolding: a deterministic
    function of already-verified values, it asserts no new claim and never touches the
    grounded slots. Copies every mutated container, so the payload stays untouched."""
    marked = dict(body)
    marker = idempotency_marker(key)
    text = marked.get("body")
    if isinstance(text, str):
        marked["body"] = (
            f"{text}\n\n---\n{marker}\n"
            f"_Idempotency key `{key}` — Tessera (best-effort deduplicated)._"
        )
    labels = marked.get("labels")
    if isinstance(labels, list):
        marked["labels"] = [*labels, _idempotency_label(key)]
    return marked


@dataclass(frozen=True)
class GithubActuator:
    """The opt-in real actuator: it binds ``{owner}``/``{repo}`` (a deployment binding,
    not evidence) into the grounded request and sends it to GitHub — **iff** it is
    approved and holds a credential. Missing either, it declines and records why
    (``outcome="blocked"``, ``sent=False``), so ``sent=True`` is *earned*, never a
    rubber stamp. A transport error records ``outcome="error"`` and ``sent=False``.
    Before creating, it runs a best-effort idempotency pre-check (Milestone 15, ADR
    0026): a verified prior identical action yields ``outcome="exists"`` and an
    undecidable pre-check yields ``outcome="inconclusive"`` — both ``sent=False``, never
    a silent duplicate.

    Pure-stdlib (``urllib``); no new dependency, no pip extra. The opt-in is
    constructing this class with a credential + an explicit ``owner``/``repo`` binding.
    It is **never constructed by the default path**, and its real HTTP transport
    (:class:`_UrllibTransport`) and the real network are **never invoked in CI**:
    Tessera renders and simulates in this repository (ADR 0025). Tests construct it and
    exercise its ``execute`` against an injected fake :class:`Transport`; the real
    network is never touched."""

    owner: str
    repo: str
    # repr=False: the credential must never surface in repr()/str() — a traceback or
    # debug print of the actuator would otherwise leak the PAT (audit B3).
    token: str | None = field(default=None, repr=False)
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

        # Approved AND credentialed: form the real, best-effort-idempotent request. The
        # key is a pure function of the grounded payload; the marker is deployment
        # scaffolding embedded into a copy of the body (the payload is untouched).
        key = idempotency_key(payload)
        marked_body = _embed_idempotency(payload.body, key)
        bound_path = self._bind(payload.path)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }

        # Pre-send existence check on the primary (immediately-consistent) endpoint —
        # never silently create over an already-existing or an undecidable result.
        verdict, detail = self._existing(payload, bound_path, key, headers)
        if verdict == "inconclusive":
            return _receipt(
                payload,
                actuator=self.name,
                path=bound_path,
                body=marked_body,
                outcome="inconclusive",
                idempotency_key=key,
                result={
                    "reason": (
                        "the idempotency pre-check could not confirm the target is "
                        "free of a prior identical action; nothing created."
                    ),
                    "detail": detail,
                },
                approved=True,
            )
        if verdict == "exists":
            return _receipt(
                payload,
                actuator=self.name,
                path=bound_path,
                body=marked_body,
                outcome="exists",
                idempotency_key=key,
                result={
                    "reason": (
                        "an identical grounded action already exists at the target "
                        "(matched idempotency key); nothing created."
                    ),
                    "existing": detail,
                },
                approved=True,
            )

        url = self.base_url + bound_path
        try:
            status, response = self.transport.post(
                url, headers=headers, body=marked_body
            )
        except (urllib.error.URLError, OSError) as exc:  # pragma: no cover - real net
            return _receipt(
                payload,
                actuator=self.name,
                path=bound_path,
                body=marked_body,
                outcome="error",
                idempotency_key=key,
                result={"error": f"transport error; nothing created: {exc}"},
                approved=True,
            )
        if not 200 <= status < 300:
            return _receipt(
                payload,
                actuator=self.name,
                path=bound_path,
                body=marked_body,
                outcome="error",
                idempotency_key=key,
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
            path=bound_path,
            body=marked_body,
            executed=True,
            simulated=False,
            sent=True,
            outcome="created",
            idempotency_key=key,
            result={"status": status, "response": response},
            approved=True,
        )

    def _existing(
        self,
        payload: RenderedPayload,
        bound_path: str,
        key: str,
        headers: dict[str, str],
    ) -> tuple[str, dict[str, object] | None]:
        """Best-effort pre-check on the target's **primary** (immediately-consistent)
        list endpoint — the repo's issues list (``state=all``, **unfiltered**) or the
        PR's comments list — **paging** until the exact marker is found in a
        candidate's body, the listing is exhausted (a short page), or the page cap is
        hit. Returns ``("exists", issue)`` on a verified hit, ``("inconclusive",
        detail)`` when a page read errors / is non-2xx **or** the cap is reached before
        the listing is fully scanned (refuse, never duplicate), or ``("create", None)``
        when the target is free of a prior identical action.

        The scan is deliberately **label-independent** (audit B2): an earlier design
        filtered the issues list by the ``idem-`` label, which made dedup silently
        depend on that label surviving — dropped at create (a PAT that cannot create
        labels), deleted later, or stripped by GitHub, the filter would return empty
        and a re-run would duplicate despite the body marker. Scanning the unfiltered
        listing costs more pages on a busy repo (the cap then yields an honest
        ``inconclusive``) and buys correctness on the only signal that is verified
        anyway: the exact marker substring. The eventually-consistent search index is
        deliberately not used, so the residual is a genuine concurrent create, not a
        minute of search lag."""
        marker = idempotency_marker(key)
        if payload.path.rstrip("/").endswith("/comments"):
            base = f"{self.base_url}{bound_path}?per_page={_PRECHECK_PER_PAGE}"
        else:
            base = (
                f"{self.base_url}{bound_path}?state=all&per_page={_PRECHECK_PER_PAGE}"
            )
        for page in range(1, _MAX_PRECHECK_PAGES + 1):
            try:
                status, parsed = self.transport.get(
                    f"{base}&page={page}", headers=headers
                )
            except (urllib.error.URLError, OSError) as exc:  # pragma: no cover - net
                return "inconclusive", {"error": f"pre-check transport error: {exc}"}
            if not 200 <= status < 300:
                return "inconclusive", {"status": status}
            items: list[object] = parsed if isinstance(parsed, list) else []
            for item in items:
                if isinstance(item, dict):
                    body = item.get("body")
                    if isinstance(body, str) and marker in body:
                        return "exists", {
                            "number": item.get("number"),
                            "html_url": item.get("html_url"),
                        }
            if len(items) < _PRECHECK_PER_PAGE:  # a short page = the thread's end
                return "create", None
        return "inconclusive", {
            "reason": (
                f"pre-check did not finish within {_MAX_PRECHECK_PAGES} pages; "
                "refusing rather than risk a duplicate."
            )
        }


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
