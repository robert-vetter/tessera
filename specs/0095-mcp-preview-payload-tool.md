# 0095. MCP `preview_payload` tool + a committed session

- **Phase / milestone:** Milestone 13 (spec 0093), Unit 3.
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Unit 2 built the dry-run payload renderer as a pure-stdlib layer. An enterprise agent
reaches Tessera over MCP, so the renderer needs a transport: one thin `preview_payload`
tool on `tessera-mcp` that serializes the layer verbatim — no rendering logic in the
server. The "ran on" honesty (no spend) is a committed real client↔server session that
now also previews a rendered create-issue payload, a rendered PR-comment payload, and a
withheld payload — the way the M11/M12 sessions are committed.

## Acceptance criteria

- [ ] `tessera.agent.mcp_server` gains an MCP-free handler `tool_preview_payload(action,
      domain, question)` that delegates verbatim to `payloads.preview_payload(...).to_dict()`
      — **no rendering logic** in the server.
- [ ] `build_server()` registers a `preview_payload` tool with a description and the
      `{action, domain, question}` input schema; six tools are now advertised
      (`list_domains`, `ground`, `assertions`, `list_actions`, `draft_action`,
      `preview_payload`). `SERVER_INSTRUCTIONS` mentions previewing a payload as the
      render-≠-send step after drafting.
- [ ] The **no-`mcp`-in-base-graph** pin still holds (importing the server pulls no
      `mcp`); the handler is unit-tested in CI without the SDK; the SDK wiring is
      contract-tested under `--extra agent`.
- [ ] `scripts/record_mcp_session.py` extended with payload-preview calls (a rendered
      incident create-issue, a rendered PR-comment, and a **withheld** payload for an
      incompatible/refused grounding) + a transcript renderer for them.
- [ ] `data/mcp_session/` regenerated (`uv run --extra agent python
      scripts/record_mcp_session.py`) and committed; every rendered payload shows
      `rendered`, `all_grounded`, `sent=false`, method/path, and field-traced slots; the
      withheld one shows `rendered=false` with its reason.

## Scope

**In:** the thin MCP tool + its handler, the server wiring + instructions, the
unit/contract tests, the extended recorder, the regenerated committed session.

**Out:** any rendering logic in the server (it lives in Unit 2's layer); the gated
data-derived payload-boundary measurement (Unit 4); a second target; any sending.

## Eval impact

None on the batteries (transport only). Faithfulness stays the single gate at 1.0.

## Risks / open questions

- **Keep the server thin.** The handler must `return preview_payload(...).to_dict()` and
  nothing else — the M11/M12 discipline (no logic in transport). A test asserts the
  handler output equals the layer's `to_dict()`.
- **CI stays pure-stdlib.** The recorder and the SDK contract tests need `--extra agent`;
  CI skips them, and the no-`mcp` import pin guards the default graph.
