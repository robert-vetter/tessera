# 0084. The MCP server (`tessera-mcp`)

- **Phase / milestone:** Milestone 11, Unit 4 (see spec 0081)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018)

## Problem

Unit 3 built the grounded-tool layer (`tessera.agent.grounded`): read-only,
deterministic, verifier-checked, JSON-serializable. This unit exposes it over the
**Model Context Protocol** so a real enterprise AI agent (Claude, or any MCP client)
can call Tessera as its evidence oracle — the milestone's thesis-completing surface.

The constraint (ADR 0022, spec 0081): the MCP SDK must **not** become a clone-and-run
or CI dependency. CI runs `uv sync --frozen` (base, no extras) and must stay
pure-stdlib / offline / key-free. So the SDK rides as the opt-in `agent` extra and
the server is a thin transport with **no grounding logic** of its own.

## The design

`src/tessera/agent/mcp_server.py`, in two clearly separated parts:

1. **MCP-free tool handlers** — plain functions that call the Unit-3 layer and
   return JSON-native dicts: `tool_list_domains()`, `tool_ground(domain, question)`
   (`-> ground(...).to_dict()`), `tool_assertions(domain, record_id)`. They import
   no MCP and are **unit-tested in CI** without the SDK.
2. **The MCP wiring** — `build_server() -> FastMCP` (lazily `from mcp.server.fastmcp
   import FastMCP`) registers the three handlers as MCP tools with agent-facing
   descriptions (each docstring tells the agent: claims are verifier-checked, a
   refusal is explicit, provenance is inline). `main()` runs it over **stdio**.
   `tessera-mcp` is the entry point.

**The opt-in extra.** `pyproject.toml` gains `agent = ["mcp>=1.0"]` and the
`tessera-mcp` script. `mcp` is imported **only inside `build_server()`/`main()`**, so
importing `tessera.agent.mcp_server` (and the whole default graph) never pulls it —
pinned by a test mirroring `tests/test_vectors.py::test_default_import_graph_has_no_hdbcli`.

**The "ran on" honesty.** The server is made to actually speak MCP: a real MCP client
session (list-tools, a grounded call per domain, a refusal, an assertions call) is
captured and committed as a transcript under `data/mcp_session/` — the no-spend
analogue of the Milestone-5 "ran on real data" snapshot. CI does not run it (no SDK);
it is reproducible locally with `uv run --extra agent`.

## Acceptance criteria

- [ ] `pyproject.toml`: `agent = ["mcp>=1.0"]` extra + `tessera-mcp =
      "tessera.agent.mcp_server:main"` script; `uv.lock` updated; base `uv sync
      --frozen` still installs **without** `mcp`.
- [ ] `mcp_server.py`: MCP-free handlers (`tool_list_domains`, `tool_ground`,
      `tool_assertions`) returning JSON-native dicts; `build_server()` (lazy SDK
      import) registering them as described tools; `main()` over stdio. No grounding
      logic in the server.
- [ ] **Default-import pin (CI)**: a subprocess importing `tessera.agent.mcp_server`
      asserts `mcp` is **not** in `sys.modules`.
- [ ] **Handler tests (CI)**: `tool_ground` grounds + verifies a real question and
      carries an out-of-scope one as an explicit refusal; `tool_list_domains` lists
      the three domains with descriptions; `tool_assertions` returns the ER trail —
      all without importing `mcp`.
- [ ] **Contract test (`pytest.importorskip("mcp")`)**: `build_server()` returns a
      server exposing `ground` / `assertions` / `list_domains` with non-empty
      descriptions and the expected input schemas; dispatching a tool through the
      server returns the handler's JSON. Runs where the extra is installed, skipped
      in CI.
- [ ] A committed **real MCP client-session transcript** (`data/mcp_session/`)
      showing a grounded answer per domain + a refusal, reproducible with `uv run
      --extra agent`.
- [ ] Gate green (base env, contract test skipped); faithfulness 1.0; deterministic.

## Scope

**In:** the `agent` extra + `tessera-mcp` entry point; `mcp_server.py` (handlers +
wiring + `main`); the default-import pin; handler + contract tests; the recorded
session transcript.

**Out:**
- **Any grounding logic in the server** — it only serializes the Unit-3 layer.
- **Non-stdio transports** (SSE / streamable-HTTP). The SDK supports them; stdio is
  the standard local agent transport and all this milestone needs. Recorded as a
  trivial future extension.
- **Effectful / proposing tools** — read-only only (ADR 0022).
- **Making `mcp` a hard dependency** — it stays the opt-in `agent` extra; CI stays
  pure-stdlib.
- **The boundary-trust *measurement* over gold cases** — Unit 5.

## Eval impact

- **Faithfulness held at 1.0; no battery moves.** The server is a transport over the
  already-verified Unit-3 layer; it adds no answer path. The boundary-equivalence
  measurement is Unit 5.

## Risks / open questions

- **The SDK must stay off the CI path.** Mitigated by the lazy import + the
  default-import pin + CI's `--frozen` base sync; proven by the pin test and a green
  base gate.
- **`uv.lock` churn from the SDK's transitive deps** (pydantic, starlette, uvicorn).
  Acceptable and precedented (the `cloud`/hdbcli extra is locked the same way); they
  are optional and never installed by the base sync (verified).
- **The contract test only runs where the extra is installed.** Honest and
  intentional (CI is pure-stdlib); the handlers — the substance — are fully tested in
  CI, and the wiring is contract-tested locally + demonstrated by the committed
  transcript. Documented in the test's docstring.
- **FastMCP API drift.** Pinned to `mcp>=1.0`; the wiring uses only the stable
  `FastMCP`, `@tool()`, and `run("stdio")` surface.
