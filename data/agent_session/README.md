# `data/agent_session/` — a real Claude agent, grounded only through Tessera's MCP tools

The headline demo of the project's thesis (Milestone 17, spec 0115): a **real
Claude agent** is handed *only* Tessera's seven MCP tools and must answer from
them alone — so it can only say what Tessera can prove, and only draft/execute
what Tessera grounds.

- `TRANSCRIPT.md` — the readable session: Claude's turns + the tool calls it made.
- `session.json` — the full captured exchange (every tool call + deterministic result).
- `MANIFEST.json` — provenance (`"synthetic": false`, the agent model, the date).

The three turns exercise the whole contract: a **grounded** RCA with cited
evidence; a **refusal** carried honestly (run R-1041 passed, so there is nothing
to explain — the agent says so instead of confabulating); and an **action** that
runs draft → preview → execute and ends at a **simulated** receipt
(`sent: false` — nothing is sent).

Regenerate locally (needs an Anthropic key + the `agent` extra; never run in CI):

    set -a; source .env; set +a
    uv run --extra agent python scripts/record_agent_session.py
