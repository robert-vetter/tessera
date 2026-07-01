# 0098. Milestone 14 plan: effectful execution behind approval

- **Phase / milestone:** Milestone 14 — Effectful execution behind approval: let an
  agent take a grounded, verifier-checked action (the M12 `ActionProposal`, rendered
  to an exact GitHub request in M13) and **execute it through an actuator** — with a
  **simulated default** that sends nothing (the CI-verifiable core) and an **opt-in
  real path** behind credentials + approval. The trust contract, measured across the
  read boundary (M11), the action-draft boundary (M12), and the executable-payload
  boundary (M13), is carried one boundary further: to **execution**. The M13
  `RenderedPayload.all_grounded` becomes the *gated precondition* — nothing executes
  over ungrounded ground. Post-roadmap (ROADMAP phases complete and tagged
  `phase-0`…`phase-4`; hardening `milestone-5`; embeddings-on-SAP `milestone-6`;
  embeddings-beyond-retrieval `milestone-7`; deterministic-ER-precision `milestone-8`;
  multi-field name+address ER `milestone-9`; registration-key ER `milestone-10`;
  agentic/MCP read-only grounded mode `milestone-11`; grounded actions over MCP
  `milestone-12`; dry-run executable-payload preview `milestone-13`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the two project-shaping scope questions below, which were
  asked and answered 2026-07-01)

## Problem

Milestone 13 rendered the **exact wire request** a grounded action would send — the
`RenderedPayload` (method, path, JSON body), every content value traced to a
verifier-passing field, byte-reconstructable, and **sent nothing**. Its module
docstring, ADR 0024, and the STATUS close all record the same honest edge: *render ≠
send.* `{owner}`/`{repo}` stay unbound; `sent=False`; no transport, no socket, no
credential. An agent that must actually **act** still takes that rendered request and
sends it itself, *outside* Tessera's guarantee — the last ungrounded step.

ADR 0023/0024 named this next scope precisely and told us how to do it honestly:
**effectful execution behind approval** — *"done honestly in a clone-and-run / CI
project, would consume this renderer (a simulated default actuator + an opt-in real
path + an execution receipt)."* It is the natural fourth boundary in the arc (read →
action draft → executable payload → **execute**), and it is the biggest posture
decision the project has faced — the first time Tessera would *do* something,
credentialed and (on the real path) irreversible.

The honest way to build it in a clone-and-run / CI project is the one ADR 0024 wrote
down: the **verifiable core is a simulated actuator** — it consumes an `all_grounded`
`RenderedPayload`, produces an `ExecutionReceipt`, and sends nothing (deterministic,
offline, no spend, nothing irreversible) — with the **real GitHub actuator as an
opt-in seam** behind credentials + approval, contract-tested against an injected fake
transport with its **real transport/network never invoked in CI/clone-and-run** (the
M6-embedding-seam / SAP-adapter posture). The gate that makes execution a *trust*
extension rather than a
new write surface is the M13 payload: **execution requires an `all_grounded`
`RenderedPayload`** — the execution analogue of M11's "a refusal never becomes an
answer," M12's "a refusal is carried, never drafted over," and M13's "a payload is
never rendered over ungrounded ground."

**Maintainer decisions (asked & answered 2026-07-01 — project-shaping, so asked):**

1. **The thrust — effectful execution behind approval.** Chosen over a second payload
   target (Jira create-issue), a second real connector, full HANA graph persistence,
   and BTP serving. It is the named M13 follow-through and the thesis-completing move
   ("a trust layer for enterprise AI agents" that, for the first time, can *act*),
   done in a way that keeps the verifiable core fully in CI. It carries **ADR 0025**
   (the execution boundary: the actuator, the simulated default + opt-in real seam,
   the `all_grounded` gated precondition, the receipt as the trust record, and the
   still-honest edge — nothing is sent in CI).
2. **The posture — simulated core + opt-in real seam, no real send in-repo.** Chosen
   over (a) *also* doing a maintainer-authorized real one-shot (actually creating one
   GitHub issue/comment — spend-adjacent, credentialed, an irreversible external side
   effect), and (b) simulated-only with no real adapter built at all. The chosen
   middle is: **build the simulated actuator + receipt as the CI-verifiable core, AND
   a real `GithubActuator` behind a credentialed, explicitly-enabled, approval-gated
   opt-in, contract-tested against a fake transport with its real transport/network
   never invoked in CI or the default clone-and-run.** Zero spend, nothing irreversible
   in-repo; the honest edge
   is *"would send a grounded request, gated on approval — and in this repository, we
   prove it renders and would send, without sending."* This matches the M6 embedding
   seam and the Phase-4 SAP adapters: designed-for and contract-tested, provisioning
   (here: sending) deliberately declined.

**Finer decisions (not project-shaping — decided and recorded here, per autonomous
mode):**

- **The real actuator needs no new dependency and no pip extra.** Unlike the `cloud`
  (hdbcli) and `agent` (mcp) extras, the real GitHub path is pure-stdlib
  `urllib.request` (the same posture as the Phase-4 GenAI Hub / Anthropic adapters,
  "pure stdlib HTTP"). The "opt-in" is therefore a **credential + explicit enablement
  + approval**, not a dependency install. Recorded because it is a cleaner opt-in than
  the prior two, and because "no new dependency" keeps the default graph unchanged.
- **A single hard gated precondition for any actuator: `RenderedPayload.all_grounded`.**
  `execute_action` renders the M13 payload and refuses (a withheld receipt, nothing
  executed) unless it is fully grounded — for both the simulated and the real actuator.
  This is the execution-level analogue of the refusal-carrying contract; it means the
  M13 field-grounding guarantee is exactly what gates a side effect.
- **Approval is a second, real-path gate; the simulated actuator is the safe default.**
  `execute_action(kind, domain, question, *, actuator=SimulatedActuator(), approve=False)`.
  The **simulated** actuator produces a receipt without any side effect and does not
  require approval to run (it demonstrates the contract; nothing leaves). The **real**
  `GithubActuator` refuses to send unless `approve=True` **and** it holds a credential
  — so `sent=True` is *earned*, never a rubber stamp (a provably-failable check).
  Every receipt still carries `requires_approval=True` and records whether approval
  was given, preserving the propose-and-approve contract in the artifact.
- **The simulated result is transparently synthetic.** The simulated receipt records
  the exact request that *would* be sent (from the payload) and a result explicitly
  marked simulated (`simulated=True`, `sent=False`, `outcome="simulated"`), carrying
  **no fabricated real resource** — no invented issue number or `html_url` that could
  be mistaken for a real side effect. Honesty rule: a simulation must never look like a
  real execution.
- **The receipt is a lossless trust record.** `ExecutionReceipt` carries the gated
  payload (method, path, body), the grounded slots with their recomputed verdicts and
  provenance, the actuator used, the approval, and the outcome — so an agent can audit
  *exactly* what was (or would be) sent and why it was allowed, without a second
  round-trip. This is the measured artifact of Unit 4.
- **The MCP `execute_action` tool is simulated-only.** The transport server holds no
  credentials; it wires the simulated actuator only. Real execution is a deliberate
  local/API opt-in (the Python API with an explicit `GithubActuator` + `approve=True`),
  never the MCP surface. Recorded as the conservative, honest choice — the MCP surface
  can *demonstrate* execution (simulated) without ever being able to send.
- **Idempotency is documented, not engineered.** A real create-issue is not idempotent;
  re-running would create duplicate issues. Because the real path is opt-in and never
  run in CI, M14 records this as a caller responsibility (and the receipt makes the
  intended request auditable before approval) rather than building a dedup/idempotency
  key — noted in ADR 0025 and the WRITEUP as an honest edge of the real path.

## The design (recorded for ADR 0025)

**Execution is a strict consumer of the M13 boundary; it renders no request a second
way and invents nothing.** A new layer `src/tessera/agent/execution.py` (additive,
*not* ADR 0008 frozen core) consumes `render_payload` (M13) and provides:

1. **An `Actuator` protocol** — `execute(payload: RenderedPayload, *, approved: bool)
   -> ExecutionReceipt`. Two implementations:
   - **`SimulatedActuator`** (the default): returns a receipt with `simulated=True`,
     `sent=False`, `outcome="simulated"`, the payload's exact request recorded, and a
     transparently-synthetic result. No network, no credential, deterministic.
   - **`GithubActuator`** (opt-in): holds a credential (a token) and an injected HTTP
     transport (default: a stdlib `urllib` transport; a fake transport is injected in
     tests). `execute` refuses (a receipt with `sent=False` and a reason) unless
     `approved=True` and a credential is present; otherwise it performs the POST and
     records `sent=True` with the real response. **Never constructed by the default
     path; its real transport/network never invoked in CI.**
2. **`execute_action(kind, domain, question, *, actuator=SimulatedActuator(),
   approve=False) -> ExecutionReceipt`** — renders the M13 payload for the grounded
   action; if it is **not** `all_grounded`, returns a **withheld** receipt
   (`executed=False`, `withheld=True`, the carried reason, no request, nothing sent);
   otherwise hands the grounded payload to the actuator and returns its receipt. The
   single entry point; the `all_grounded` payload is the hard precondition.
3. **`ExecutionReceipt`** (frozen dataclass, JSON-serializable via `to_dict`) — the
   lossless record: `kind`/`domain`/`question`/`target`, the request
   (`method`/`path`/`body`, empty when withheld), the grounded `slots` (the payload's
   slots, each with value + `verified` + provenance), `actuator` (`"simulated"` |
   `"github"`), `executed`, `simulated`, `sent`, `withheld` + `withheld_reason`,
   `outcome`, `result`, `payload_grounded` (the gated precondition), `requires_approval`
   (always True), and `approved`.

**Honest properties that make this a trust *extension*, not a new write surface:**

- **Nothing executes over ungrounded ground.** A refused / route-incompatible /
  wrong-domain / partially-grounded action never yields a request: `execute_action`
  withholds it (the M13 `all_grounded` gate), and the receipt carries the reason with
  no request and `sent=False`. Faithfulness (every recorded slot verifier-passing) is
  carried into the receipt.
- **The default sends nothing; the real path is double-gated and earned.** The
  simulated actuator is the default and produces no side effect. The real actuator
  refuses to send without approval **and** a credential — so `sent=True` is provably
  earned, pinned by a test (a fake-transport contract test that a POST happens only
  when approved+credentialed, and never otherwise).
- **A simulation is never dressed as a real execution.** The simulated receipt carries
  `simulated=True`/`sent=False` and no fabricated resource id — pinned by a test.
- **Deterministic, offline, pure-stdlib on the verifiable core.** The module imports
  only the payload/action layers and stdlib; the leak-guard (`tests/test_agent.py`) is
  extended to import and call `execute_action` (simulated) and confirm no embedding /
  LLM / `hdbcli` / `mcp` import reaches the verifier, and that the **simulated path
  opens no socket**.

**Where it lives.** `src/tessera/agent/execution.py` (new; additive). The MCP server
gains one thin tool — `execute_action(action, domain, question)` — transporting the
**simulated** actuator verbatim; the SDK stays the opt-in `agent` extra; the default
import graph stays free of `mcp`. The verifier (`eval/metrics.py`), `graph.py`,
`resolution.py`, `ingestion.py`, `payloads.py`, and the rest of the ADR 0008 frozen
core are **untouched** — M14 expects a **zero-line frozen-core delta** (as M12, M13).

## Success criterion

An enterprise AI agent can ask Tessera over MCP to **execute** a grounded action and
receive an `ExecutionReceipt` for a **simulated** execution — the exact request that
would be sent, every value field-grounded, and nothing actually sent — or a carried
**withheld** receipt when the action is not fully grounded, offline and in CI:

- A real MCP client session against `tessera-mcp` executes (simulated) an incident and
  a PR summary and carries a **withheld** execution for an action on
  insufficient/incompatible grounding — committed as a transcript (the "ran on"
  honesty, no spend), the way the M11/M12/M13 MCP sessions are committed; every
  simulated receipt has `sent=false`.
- **Every simulated execution consumed an `all_grounded` payload**, and the receipt is
  a **lossless** record of it (request + slots + independently-recomputed verdicts) —
  measured over cases **derived from the data** (a pinned CI test,
  `tests/test_execution_boundary.py`, the M11/M12/M13 boundary pattern), so the new
  capability's effect on the metric is *known* (principle 3).
- **Faithfulness is 1.0 across the execution boundary** — counted over every slot of
  every simulated execution's receipt; an actuator that recorded a fabricated or
  over-claimed value would fail it.
- **Nothing executes over ungrounded ground** — a refused / incompatible / partial
  action yields a withheld receipt with no request and `sent=false` (pinned, provably
  failable).
- **The real path is earned, not assumed** — `GithubActuator` sends **iff** approved
  and credentialed, pinned by a fake-transport contract test (a POST happens exactly
  then, and never in CI); a simulated receipt is never dressed as a real one.
- **The default clone-and-run + CI stay pure-stdlib** — the no-`mcp` import pin still
  holds; the execution layer adds no embedding/LLM/MCP import toward the verifier and
  no network on the simulated path (leak-guard extended). Faithfulness stays the single
  hard gate at 1.0 on every battery; no battery number moves (the layer is a consumer,
  not a new answer path).
- **Zero frozen-core delta** — the ADR 0008 empty-diff audit over `milestone-13..HEAD`
  is empty (the execution layer is additive; the MCP tool is thin transport).

## Acceptance criteria

- [ ] **Phase plan (Unit 1, spec 0098).** This plan + the two recorded scope decisions
      (asked 2026-07-01) + the finer decisions + the design for ADR 0025.
- [ ] **Actuator + `ExecutionReceipt` + ADR 0025 (Unit 2, spec 0099).**
      `src/tessera/agent/execution.py` — the `Actuator` protocol, `SimulatedActuator`
      (default), `GithubActuator` (opt-in, stdlib `urllib`, injected transport,
      approval+credential-gated, real transport/network never invoked in CI),
      `ExecutionReceipt`, and
      `execute_action` **gated on `RenderedPayload.all_grounded`**. Simulated result
      transparently synthetic; real `sent=True` earned (fake-transport contract test);
      withheld-never-executed; JSON-serializable receipt. Leak-guard extended
      (simulated path pulls no MCP/embedding import and opens no socket). Full stdlib
      coverage. **ADR 0025** records the execution boundary (simulated default + opt-in
      real seam, the `all_grounded` gated precondition, approval gate, render-in-CI /
      send-never, the receipt as the trust record) + the rejected scopes (a real
      one-shot; simulated-only; an MCP-exposed real actuator; engineered idempotency).
      **Mandated pre-merge adversarial multi-agent review** (the new trust-bearing
      surface — the first that can produce a side effect).
- [ ] **MCP execute tool + session (Unit 3, spec 0100).** `execute_action` on
      `tessera-mcp` — thin transport, simulated actuator only, no execution logic; the
      no-`mcp`-in-base-graph pin holds; contract test of the wiring; the committed
      `data/mcp_session/` session regenerated to add a simulated execution of an
      incident and a PR summary and a withheld execution (`sent=false` throughout).
- [ ] **Trust across the execution boundary (Unit 4, spec 0101).** A pinned CI test
      (`tests/test_execution_boundary.py`): over cases derived from the data (every
      failed run, every PR), every simulated execution consumed an `all_grounded`
      payload and its receipt is a lossless record (request + slots +
      independently-recomputed verdicts); faithfulness 1.0 across the execution
      boundary; a withheld action carries no request and nothing sent; the real path
      sends iff approved+credentialed (fake transport). ADR 0005/0006 re-examined at
      the execution boundary and recorded **still not forced**.
- [ ] **Close (Unit 5, spec 0102).** Gate green under multiple `PYTHONHASHSEED` values;
      WRITEUP "effectful execution behind approval" section (the actuator, the
      simulated core, the opt-in real seam, the `all_grounded` gate, render-in-CI /
      send-never, the honest edges — idempotency, the untaken real one-shot); README
      (the execute tool + the corrected scope: simulated by default, real path opt-in
      behind credentials+approval, nothing sent in CI); CHANGELOG `[milestone-14]`;
      ADR 0025 nav + index; the ADR 0008 **empty-diff core audit** run and confirmed
      empty; STATUS; tag `milestone-14`; memory; next-milestone kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0098 | this plan + the two recorded scope decisions (asked 2026-07-01) + finer decisions + the design for ADR 0025 |
| 2 | 0099 | `src/tessera/agent/execution.py` — `Actuator`/`SimulatedActuator`/`GithubActuator`/`ExecutionReceipt`/`execute_action`, gated on `all_grounded`, simulated default + opt-in real seam (stdlib urllib, injected transport, approval+credential-gated, real transport/network never invoked in CI), leak-guard extended; **ADR 0025**; **adversarial review** |
| 3 | 0100 | `tessera-mcp` `execute_action` tool (thin transport, simulated only); no-`mcp`-in-base pin holds; wiring contract test; committed real client-session transcript (simulated execution + withheld) |
| 4 | 0101 | trust across the execution boundary: simulated executions consumed grounded payloads + lossless receipts + faithfulness 1.0; nothing-over-ungrounded pin; real-path-sends-iff-approved+credentialed (fake transport); pinned CI measurement; ADR 0005/0006 re-examined and recorded unforced |
| 5 | 0102 | close: WRITEUP/README/CHANGELOG/STATUS, ADR nav/index, empty-diff core audit, tag `milestone-14`, memory, kickoff |

**Out (explicitly):**

- **Actually sending anything in this repository / CI.** The simulated actuator is the
  default and the only actuator the tests, CI, clone-and-run, and the MCP surface use.
  The real `GithubActuator` is built and contract-tested against a **fake** transport,
  never against real GitHub. No maintainer-authorized real one-shot is taken (the
  maintainer chose the no-real-send posture); if wanted later it is a separate,
  credentialed, spend-adjacent, irreversible decision (recorded in ADR 0025).
- **The MCP surface being able to send.** The `execute_action` MCP tool wires the
  simulated actuator only; the server holds no credential and can never send.
- **A second target system (Jira) or a multi-target actuator abstraction.** One target:
  GitHub, via the M13 renderer. Future work; the field-grounding + gating contract
  would carry over.
- **An LLM anywhere on the execution path.** Execution is deterministic; the request is
  the M13 deterministic template over verified fields. ADR 0005/0006 triggers
  re-examined at the execution boundary and recorded not forced.
- **Engineered idempotency / a dedup key on the real path.** Documented as a caller
  responsibility (the receipt makes the intended request auditable before approval),
  not built (the real path is opt-in and out of CI).
- **A `business` action / execution kind.** Out of scope (as M12/M13): the catalog
  stays the two DevEx-shaped kinds grounded in existing RCA/summary paths.
- **Embeddings / the M6–M7 cloud regime.** Untouched. No cloud, no online run, no spend.
- **A new gated eval metric.** Faithfulness stays the single hard CI floor at 1.0; the
  execution field-grounding / lossless-receipt measurement is a *pinned* test, not a
  new gate (the M11/M12/M13 pattern).
- **A new frozen-core change.** M14 expects a zero-line frozen-core delta; if one proves
  necessary it gets its own ADR and a pre-merge review (none is anticipated).

## Eval impact

- **Faithfulness — held at 1.0, now *also across the execution boundary*.** As in
  M11/M12/M13, the headline is a property preserved under a new projection: every slot
  of every simulated execution's receipt is backed by a verifier-passing field, the
  receipt's request equals the M13 rendered payload (lossless), and nothing executes
  over ungrounded ground. Measured (Unit 4), not assumed.
- **Coverage / quality — unchanged.** The execution layer is a consumer of existing
  proposals/payloads, not a new answer path; the batteries' numbers must not move
  (proven at close, not assumed).
- **No new gated metric.** Execution field-grounding + lossless-receipt stays *pinned*,
  not gated; faithfulness remains the single invariant floor.

## Risks / open questions

- **The first surface that can produce a side effect.** Mitigated structurally: (a) the
  simulated actuator is the default everywhere the repo runs; (b) the real actuator is
  double-gated (approval **and** credential) and never constructed in CI; (c) the MCP
  surface wires the simulated actuator only; (d) `execute_action` refuses without an
  `all_grounded` payload; and (e) the **mandated pre-merge adversarial review** on this
  trust-bearing surface. The review must specifically probe: a smuggled/over-claimed
  value in the receipt vs. the payload, a simulated receipt masquerading as sent, the
  real actuator sending without full gating, and any path where `sent=True` is not
  earned.
- **"Grounded execution" must not become decorative.** The receipt must be a *lossless*
  projection of the M13 payload (which is itself byte-reconstructable from verified
  fields), not a lenient re-summary. Pinned by Unit 4 (receipt request == rendered
  payload request; each slot's verdict recomputed independently from the grounding).
- **The simulated result honesty.** A simulation carrying a real-looking issue id/URL
  would be a dishonest "success." Pinned: the simulated receipt is transparently marked
  and carries no fabricated resource.
- **Idempotency / irreversibility of the real path.** Recorded as an honest edge of the
  opt-in path (ADR 0025, WRITEUP): a real create-issue is not idempotent; the receipt
  makes the request auditable before approval, but re-running would duplicate. Out of
  scope to engineer; named plainly.
- **Render ≠ send remains true in this repository.** M13's honest edge is preserved: in
  CI, clone-and-run, and the MCP surface, nothing is sent. M14 adds the *capability* to
  send behind an opt-in, and proves the verifiable core (simulated) and the earned real
  gate — without sending.
- **Adversarial review scope.** M14 has no frozen-core change, but the execution layer
  is a new trust-bearing surface (the first that can cause a side effect), so it carries
  a pre-merge adversarial multi-agent review — honoring the maintainer's mandate where
  the real risk lives.
