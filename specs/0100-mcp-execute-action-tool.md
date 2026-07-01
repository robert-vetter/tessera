# 0100. MCP execute_action tool — run the simulated actuator over the protocol

- **Phase / milestone:** Milestone 14 — Effectful execution behind approval (Unit 3).
  See the plan (spec 0098) and ADR 0025.
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Milestone 14 Unit 2 built the execution layer (`execute_action` → `ExecutionReceipt`,
gated on the M13 `all_grounded` payload; a simulated default that sends nothing, an
opt-in real actuator that never runs in CI). This unit exposes it over MCP so an
enterprise AI agent can drive execution the way it already drives grounding, drafting,
and payload preview — through one thin, serializable tool — while keeping the honest
edge intact: **the MCP surface can only simulate.** The transport server holds no
credential and wires the **simulated** actuator only; real execution stays a deliberate
local/API opt-in, never a network-reachable tool.

## Acceptance criteria

- [ ] `tessera-mcp` advertises a seventh tool, `execute_action(action, domain,
      question)`, that delegates verbatim to `execute_action` (the execution layer) —
      **no execution logic in the server**. A contract test pins the handler output ==
      the layer's `to_dict()`.
- [ ] The tool runs the **simulated** actuator only; `sent` is always false; a
      not-fully-grounded action is withheld with no request. The tool description states
      this plainly (nothing sent; the server holds no credential; the real actuator is
      not exposed).
- [ ] The **no-`mcp`-in-base-graph** pin still holds (importing the server module pulls
      no `mcp`); the SDK stays the opt-in `agent` extra; the wiring is contract-tested
      where the extra is installed (skipped in CI).
- [ ] `build_server()` registers all seven tools with the expected input schemas; a new
      extra-gated test dispatches `execute_action` through the protocol and asserts a
      grounded, simulated, `sent=false` receipt.
- [ ] The committed `data/mcp_session/` session (regenerated with `--extra agent`) adds
      a simulated create-issue execution, a simulated PR-comment execution, and a
      withheld execution — `sent=false` throughout.
- [ ] Gate green; **zero frozen-core delta**.

## Scope

**In:** the thin `execute_action` MCP tool + its description, the handler contract test,
the registered-tools/schema assertions, the extra-gated protocol test, and the
regenerated committed session. Additive to the agent transport layer only.

**Out:** any execution logic in the server (it delegates); exposing the real
`GithubActuator` over MCP (the server holds no credential — never); the CI-gated
boundary property (Unit 4); a second target; any frozen-core change.

## Eval impact

None to the batteries — the MCP tool is thin transport over the execution layer (itself
a consumer, not a new answer path). Faithfulness stays the single gated floor at 1.0.
The tool's fidelity is pinned by the byte-equal contract test.

## Risks / open questions

- **The MCP surface must never be able to send.** Mitigated by construction: the tool
  calls `execute_action` with the default `SimulatedActuator`; the server holds no
  credential; a test asserts `sent=false` and the simulated actuator. Recorded in the
  tool description and the server instructions.
- **Thin transport must stay thin.** The byte-equal handler contract test fails if the
  server ever adds logic over the layer (the M11/M12/M13 pattern).
