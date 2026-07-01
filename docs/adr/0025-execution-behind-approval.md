# 0025. The execution boundary: effectful execution behind approval, simulated by default

- **Status:** accepted
- **Date:** 2026-07-01

## Context

Through thirteen milestones the trust substrate climbed one boundary per milestone,
each measured and CI-gated: grounded **answers** (M11, ADR 0022), grounded **action
drafts** (M12, ADR 0023), and the **executable payload** (M13, ADR 0024) — the exact
GitHub wire request a grounded action would send, byte-reconstructable from
verifier-passing fields, and **sent nothing** (`sent=False`; `{owner}`/`{repo}`
unbound). ADR 0023 and ADR 0024 both named the next scope precisely and deferred it:
**effectful execution** — "effectful, credentialed, and potentially irreversible —
outside the honest scope of a trust layer" — and both recorded *how it would be done
honestly in a clone-and-run / CI project*: it "would **consume** this renderer (a
simulated default actuator + an opt-in real path + an execution receipt)."

Milestone 14 takes that step. The maintainer's M14 scope (asked & answered
2026-07-01, spec 0098): **(1) the thrust** is effectful execution behind approval (over
a second payload target, a second connector, HANA persistence, or BTP serving); **(2)
the posture** is a **simulated core + an opt-in real seam that sends nothing in this
repository** — build the simulated actuator + receipt as the CI-verifiable core *and* a
real GitHub actuator behind a credentialed, approval-gated opt-in, contract-tested
against a fake transport with its **real transport and network never invoked in CI or
the default clone-and-run** (declining both a maintainer-authorized real one-shot and a
simulated-only build with no
real adapter). The question this ADR settles: *what* execution is, *how* the trust
contract extends from a rendered payload to an execution, and where the honest edge is
now that Tessera can, for the first time, act.

The reversal of ADR 0023/0024's "declined effectful execution" is deliberate and
recorded here. Those ADRs declined it as effectful/credentialed/irreversible and
outside a trust layer's scope; M14 takes it in the one posture that keeps the honest
scope intact — **the verifiable core actuates nothing, and the real path is an opt-in
seam the repository never exercises.** "Render ≠ send" (M13) is preserved everywhere the
repo runs; M14 adds the *capability* to send behind an explicit opt-in and proves the
gate that makes a side effect grounded — without sending.

## Decision

**Execution is a strict consumer of the M13 boundary, gated on a fully-grounded
payload.** A small layer (`tessera/agent/execution.py`, additive, *not* ADR 0008 frozen
core) consumes `render_payload` (M13) and provides an `Actuator` seam and a single
gated entry, `execute_action(kind, domain, question, *, actuator=SimulatedActuator(),
approve=False) -> ExecutionReceipt`. It renders no request a second way and invents
nothing.

**Nothing executes over ungrounded ground.** `execute_action` renders the M13 payload
and, unless it is `all_grounded`, returns a **withheld** `ExecutionReceipt` — no
request, `executed=False`, `sent=False`, the reason carried. An actuator is *never
handed an ungrounded payload*: the gate lives in `execute_payload`, before dispatch, so
it holds uniformly for every actuator (including a real, approved, credentialed one).
This is the execution-level analogue of ADR 0022's "a refusal never becomes an answer,"
ADR 0023's "a refusal is carried, never drafted over," and ADR 0024's "a payload is
never rendered over ungrounded ground." The M13 field-grounding guarantee is exactly
what gates a side effect.

**The default sends nothing and is transparently simulated.** `SimulatedActuator` is
the default everywhere the repo runs (tests, CI, the MCP surface). It records the exact
request that *would* be sent — lossless with respect to the M13 payload (same method,
path, body, and grounded slots with their verdicts and provenance) — and a
transparently-synthetic result marked `simulated=True` / `sent=False`, carrying **no
fabricated resource id** (no invented issue number or `html_url`). A simulation must
never be dressed as a real execution.

**The real path is an opt-in seam, double-gated, and `sent=True` is earned.**
`GithubActuator` binds `{owner}`/`{repo}` (a deployment binding, not evidence) into the
grounded path and POSTs to GitHub **iff** `approved=True` **and** it holds a credential;
missing either, it declines (`outcome="blocked"`, `sent=False`) and records why. It uses
only stdlib `urllib` — **no new dependency and no pip extra** (unlike the `cloud`/`agent`
extras); the opt-in is a credential + an explicit `owner`/`repo` binding + approval. Its
HTTP transport is injected, so tests drive it against a **fake** transport and the real
network is never touched; it is **never constructed by the default path**, and its real
transport and the real network are **never invoked in CI** (the actuator itself is
contract-tested in CI against the fake transport). `sent=True` therefore requires the
full gate — a provably-failable
check, pinned by tests (a POST happens exactly when approved+credentialed on a grounded
payload, and never otherwise).

**The receipt is the lossless trust record.** `ExecutionReceipt` (frozen, JSON-
serializable) carries the gated request (method/path/body — empty when withheld), the
grounded `slots` with recomputed verdicts and inline provenance, the actuator used, the
`payload_grounded` precondition, `executed`/`simulated`/`sent`/`withheld`, the `outcome`
(`withheld` | `simulated` | `created` | `blocked` | `error`), the `result`,
`requires_approval` (always true), and `approved`. `all_grounded` on the receipt
describes the *request* (grounded, every slot verifier-passing) independent of whether
it was approved or sent — so an agent can audit exactly what was, or would be, sent and
why it was allowed.

**Posture and packaging are unchanged from ADR 0022–0024.** The layer is additive,
pure-stdlib on the verifiable core, and deterministic; the leak-guard is extended so
executing pulls no embedding / LLM / cloud / MCP import toward the verifier and the
simulated path opens no socket. The MCP server gains one thin tool (`execute_action`,
Unit 3) wired to the **simulated actuator only** — the transport server holds no
credential and can never send; the SDK stays the opt-in `agent` extra and the default
import graph stays free of `mcp`.

## Consequences

- **The trust substrate now covers the act, not just the drafted request** — and the
  coverage is *measured*: over cases derived from the data (every failed run, every PR),
  every simulated execution consumed an `all_grounded` payload and its receipt is a
  lossless record; nothing executes over ungrounded ground; faithfulness is 1.0 across
  the execution boundary (spec 0101, a pinned CI property; the M11/M12/M13 pattern).
  Faithfulness stays the single hard gate at 1.0.
- **Render ≠ send is preserved in this repository.** In CI, clone-and-run, and the MCP
  surface, nothing is sent. M14 adds the *capability* to send behind an opt-in and
  proves the verifiable core (simulated) and the earned real gate — without sending.
- **The structural-verifier limit (ADR 0005) carries through unchanged:** a slot
  `verified=True` means its value is mechanically supported by its citation, not that
  performing the action is wise. Approval — a human or agent decision — is the second
  gate on the real path, and the approver still judges.
- **Idempotency / irreversibility are an honest edge of the real path.** A real
  create-issue is not idempotent; re-running would create duplicate issues. The receipt
  makes the intended request auditable before approval, but M14 does not engineer a
  dedup / idempotency key (the real path is opt-in and out of CI). Named plainly here
  and in the WRITEUP.
- **Honest synthetic-data note (carried from ADR 0024):** the synthetic DevEx PR ids
  are `PR-NNN`, used verbatim as the grounded resource id in the bound path; real GitHub
  addresses the numeric PR number. The shape and grounding of the request are real; the
  resource id reflects our data.

## Alternatives considered

- **A maintainer-authorized real one-shot** (actually create one GitHub issue/comment in
  a throwaway repo, recorded as a real receipt — the "ran on SAP" M6/M7 analogue).
  Offered and **declined** by the maintainer for M14: it is credentialed, spend-adjacent,
  and an irreversible external side effect. The seam is built and contract-tested so the
  one-shot is a small, separate, later decision if wanted.
- **Simulated-only, no real adapter.** Declined: building the `GithubActuator` behind an
  opt-in (contract-tested against a fake transport, its real send never invoked) proves
  the real path is *real* — the request
  binds, authenticates, and would send — without sending, which is a stronger and more
  honest claim than leaving it entirely unbuilt.
- **Exposing the real actuator over MCP.** Rejected: the transport server holds no
  credential and wires the simulated actuator only, so the MCP surface can *demonstrate*
  execution (simulated) but can never send. Real execution is a deliberate local/API
  opt-in, not a network-reachable tool.
- **A dependency/extra for the real path (like `cloud`/`agent`).** Unnecessary: the real
  actuator is pure-stdlib `urllib` (the Phase-4 GenAI Hub / Anthropic adapter posture),
  so the default import graph is unchanged and the opt-in is a credential + enablement +
  approval, not an install.
- **Engineered idempotency / a dedup key on the real path.** Deferred: documented as a
  caller responsibility (the receipt is auditable before approval), not built, because
  the real path is opt-in and never run in CI.
- **An LLM-narrated execution summary (ADR 0013 narration).** Declined: the receipt
  carries grounded facts (the M13 verified fields) deterministically; narrated prose
  would cross the determinism line for a capability the template covers honestly. The
  ADR 0005/0006 triggers are re-examined at the execution boundary (spec 0101) and
  recorded **not forced**.
