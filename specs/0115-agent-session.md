# 0115. Milestone 17 Unit 4: a real Claude agent, grounded only through Tessera's MCP tools

- **Phase / milestone:** Milestone 17 Unit 4 — see spec 0112.
- **Issue:** —
- **Status:** implemented

## Problem

Through fourteen milestones "a trust layer for enterprise AI agents" was
measured, but the *agent* in that sentence was always a test harness or a
scripted MCP client — never an actual LLM. The strongest possible demonstration
of the thesis is a **real LLM agent given only Tessera's tools**, shown citing,
refusing, and getting its action gated. This is the M6/M7 "ran on X" analogue
for the agentic claim.

## Acceptance criteria

- [x] `scripts/record_agent_session.py` (maintainer-run, never CI) spawns the
      real `tessera-mcp` stdio server, bridges its seven tool schemas to the
      Anthropic Messages API tool-use format, and runs a real Claude agent
      (default `claude-sonnet-5`) through a tool-use loop where **the only
      tools are Tessera's** — under a system prompt forbidding any fact not
      obtained from a tool and requiring a refusal to be reported, not
      overridden.
- [x] Recorded live (2026-07-03, maintainer's key) to `data/agent_session/`
      (`TRANSCRIPT.md` + `session.json` + `MANIFEST.json`), exercising the
      three behaviours in three turns:
      - **grounded** — R-1042 RCA: the agent cites `Run:R-1042`,
        `run_R-0987:chunk5`, `Ticket:DEVEX-187`, `PR:PR-198` and the diff hunk;
      - **refused** — R-1041 *passed*, so `ground` returns `grounded: false`
        and the agent says "run R-1041 did not fail … no fabricated
        explanation is being offered";
      - **acted** — draft → preview_payload → execute_action ends at a
        **simulated** receipt (`sent: false`, `simulated: true`,
        `requires_approval: true`).
- [x] The MCP server, the boundary, and every engine layer are **unchanged** —
      the recorder is a pure consumer (a sibling of
      `scripts/record_mcp_session.py`); no `src/` change. Gate green.

## Scope

**In:** the recorder + the committed artifact + this spec. **Out:** running the
agent in CI (needs a key + the SDK + network — the committed transcript is the
artifact, per the recorded-run pattern); any change to the MCP tools or the
engine; the hosted UI (Unit 3, done) and packaging (Unit 5).

## Eval impact

None — a recorded demonstration over the unchanged tools. The agent's phrasing
is non-deterministic (an LLM); the tool *results* are deterministic, and the
committed transcript is honest about being a captured real run.

## Risks / open questions

- Re-running yields different phrasing (the model) but the same tool results
  and the same three outcomes (grounded / refused / simulated). If a future
  run ever showed the agent overriding a refusal, that would be a finding to
  report — the system prompt forbids it and this run obeyed.
- The recorder uses raw `urllib` for the Anthropic call *inside the script*
  (not the engine), so the leak-guard is untouched (scripts are not imported
  at runtime).
