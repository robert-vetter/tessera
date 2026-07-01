# 0099. The execution actuator + ExecutionReceipt (effectful execution behind approval)

- **Phase / milestone:** Milestone 14 — Effectful execution behind approval (Unit 2).
  See the plan (spec 0098) and **ADR 0025**.
- **Issue:** —
- **Status:** approved (autonomous mode; the two project-shaping decisions were asked
  & answered 2026-07-01, recorded in spec 0098)

## Problem

Milestone 13 renders the exact GitHub request a grounded action would send
(`RenderedPayload`) and **sends nothing**. The last step — actually acting — is still
taken by the agent outside Tessera's guarantee. Milestone 14 takes it honestly: a
pluggable **actuator** consumes the M13 payload, with a **simulated default** that
produces a receipt and sends nothing (the CI-verifiable core), and an **opt-in real**
GitHub path behind a credential + approval. The M13 `RenderedPayload.all_grounded` is
the gated precondition: **nothing executes over ungrounded ground.**

This unit builds the layer and its ADR, and — as the first Tessera surface that can
produce a side effect — carries the **mandated pre-merge adversarial multi-agent
review**.

## Acceptance criteria

- [ ] `src/tessera/agent/execution.py` (additive, not frozen core): an `Actuator`
      protocol; `SimulatedActuator` (the default); `GithubActuator` (opt-in, stdlib
      `urllib`, an injected `Transport`, approval + credential gated, its real transport
      never invoked in CI); `ExecutionReceipt` (JSON-serializable, lossless);
      `execute_payload` /
      `execute_action` gated on `RenderedPayload.all_grounded`.
- [ ] **Nothing executes over ungrounded ground** — a refused / route-incompatible /
      wrong-domain / unknown-run / partially-grounded action yields a **withheld**
      receipt (`executed=False`, no request, `sent=False`), even with a real,
      approved, credentialed actuator (the gate is before dispatch). Pinned + provably
      failable (a hand-built unverified-slot payload is withheld).
- [ ] **The simulated default sends nothing and is transparently synthetic** — the
      receipt records the exact would-be request (lossless wrt the M13 payload), marks
      `simulated=True`/`sent=False`, and carries **no fabricated resource id**. The
      simulated path opens no socket (pinned by patching `urlopen` to raise).
- [ ] **`sent=True` is earned** — `GithubActuator` performs a POST **iff** approved
      **and** credentialed, to the `{owner}`/`{repo}`-bound path (no placeholders left),
      against an injected fake transport; without either it declines (`outcome="blocked"`,
      nothing sent); a non-2xx is an `error`, not a send. The real network is never
      touched in tests or CI.
- [ ] **Leak-guard extended** (`tests/test_agent.py`): importing + calling
      `execute_action` pulls no embedding / LLM / `hdbcli` / `mcp` module toward the
      verifier.
- [ ] **ADR 0025** records the execution boundary and the rejected scopes.
- [ ] **Pre-merge adversarial multi-agent review** run; findings triaged and fixed
      before merge; regressions pinned.
- [ ] Gate green (format, lint, mypy strict, tests, eval floor 1.0) under multiple
      `PYTHONHASHSEED` values; **zero frozen-core delta**.

## Scope

**In:** the execution layer, its unit tests (`tests/test_execution.py`), the leak-guard
extension, and ADR 0025. The layer consumes `render_payload` (M13); it grounds nothing
a second way and invents nothing.

**Out:** actually sending anything in this repo/CI (the real actuator is contract-tested
against a fake transport only); the MCP `execute_action` tool (Unit 3); the CI-gated
boundary property (Unit 4); a second target (Jira); engineered idempotency on the real
path (documented, not built); any `business` action; any LLM on the path; any
frozen-core change.

## Eval impact

None to the batteries — the execution layer is a consumer of existing payloads, not a
new answer path. Faithfulness stays the single gated floor at 1.0. The
field-grounding / lossless-receipt property is measured as a *pinned* test in Unit 4;
this unit's tests pin the actuator contract itself.

## Risks / open questions

- **The first surface that can cause a side effect.** Mitigated structurally (simulated
  default; real path double-gated + never in CI; ungrounded gate before dispatch;
  `sent=True` earned) and by the **mandated adversarial review**, which must probe: a
  receipt value that over-claims vs. the payload; a simulated receipt masquerading as
  sent; the real actuator sending without full gating; any `sent=True` that is not
  earned; and any placeholder left unbound on a real send.
- **Simulation honesty.** A simulated receipt carrying a real-looking resource id would
  be a dishonest "success" — pinned against.
- **Idempotency / irreversibility of the real path** — an honest edge, recorded in
  ADR 0025 (a real create-issue is not idempotent; the receipt makes the request
  auditable before approval), not engineered here.
