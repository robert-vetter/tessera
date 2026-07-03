# 0113. Milestone 17 Unit 2: narration live + presentation cosmetics

- **Phase / milestone:** Milestone 17 Unit 2 — see spec 0112.
- **Issue:** —
- **Status:** implemented

## Problem

The ADR 0013 narration boundary was contract-tested against fakes but **never
exercised live** (audit inventory); the `:trust` panel printed raw repr floats
(`0.8888888888888888`); the MCP `serverInfo.version` reported the SDK's version
instead of the project's. All presentation, no trust-model change.

## Acceptance criteria

- [x] **Narration verified live** (2026-07-03, maintainer's key, default Haiku
      model): `TESSERA_NARRATOR=anthropic uv run tessera-chat --vertical devex`
      rendered a narration paragraph **below** the canonical claims under the
      label "≈ narration (LLM-phrased from the verified claims; not
      evidence)", with `✓ trust: 8/8 claims verifier-checked` above it. The
      observed narration carried only claim-borne facts (R-1042, 30s timeout,
      the incident + PR trail). Refusals stay un-narrated by construction
      (`_render_turn` returns before the narrator on ungrounded answers —
      pinned by the existing key-free test). Live output quoted in STATUS;
      not committed as an artifact (nondeterministic by nature).
- [x] `:trust` renders floats at the eval's three-decimal reporting precision
      (`_metric`); pinned by `test_trust_panel_rounds_recorded_metrics`.
- [x] MCP `serverInfo.version` reports `importlib.metadata.version("tessera")`
      — FastMCP exposes no public version parameter (signature checked), so
      `build_server()` sets it on the underlying low-level server; pinned by
      `test_server_info_reports_the_project_version` so an SDK rename
      surfaces as a test failure, not a silent revert.
- [x] Gate green; eval untouched (narration is outside the eval, ADR 0013).

## Scope

**In:** the three items above. **Out:** any change to `narration.py`'s
boundary/guard (it worked as designed on first live use); evidence-text
rendering (stays verbatim, spec 0112 decision 3); the UI (Unit 3).

## Eval impact

None — presentation only; the narrator is not on any measured path.

## Risks / open questions

- Live narration output varies per call; the *guard* (novelty rejection) and
  the *label* are the invariants, both deterministic and tested.
- `server._mcp_server` is an SDK-internal attribute — cosmetic only, and the
  contract test turns an SDK change into a visible failure.
