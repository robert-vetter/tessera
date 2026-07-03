# 0112. Milestone 17 plan: demoable to humans

- **Phase / milestone:** Milestone 17 — Act 2's second milestone
  ([`docs/ROADMAP2.md`](../docs/ROADMAP2.md)): make the measured engine
  presentable to people who don't read terminals, **without changing the trust
  model**. Post `milestone-16` (M15's real send is on the record).
- **Issue:** —
- **Status:** approved (autonomous mode, spec 0018; maintainer directed the
  start on 2026-07-03 — "anthropic key ist wieder drin genauso wie die hana
  sachen, starte M17").

## Problem

The audit's demo verdict: strong for an SAP engineer, weak for everyone else —
everything is a terminal, answers surface raw evidence chunks, there is no way
to *show* the product in under three minutes. The maintainer has publicly
committed (Z Fellows) to "a live demo anyone can try" within the month. M17
builds the presentation layer as a strict *consumer* of the existing trust
objects: `GroundedResult`, `ActionProposal`, `RenderedPayload`,
`ExecutionReceipt`. **No new answer path, no new claims, no verifier change.**

**Recorded decisions (autonomous mode):**

1. **UI stack: pure stdlib (`http.server`), no new dependency, no extra**
   (carries **ADR 0027**). The engine's story is "zero runtime dependencies,
   clone-and-run"; the UI keeps it — server-rendered HTML + inline CSS/vanilla
   JS, `tessera/ui/`. Rejected: FastAPI/Flask (a web-framework dependency and
   its CVE/upgrade surface for one page), an SPA (a build toolchain for a
   demo whose substance is server-side truth).
2. **The UI holds no credential and can cause no real side effect by
   construction.** Its action flow drives the **simulated** actuator only
   (the MCP posture, ADR 0025); the real path stays maintainer-only outside
   the UI. Hosted mode therefore needs no special "read-only flag" — the app
   is stateless over committed data, and without `ANTHROPIC_API_KEY` narration
   simply stays off (`TESSERA_NARRATOR` unset → deterministic rendering).
3. **Evidence text stays verbatim everywhere.** The "raw markdown chunk"
   critique is answered by *presentation* (narration above canonical claims;
   the UI renders chunks as preformatted evidence), never by munging evidence
   text. LLMs present; they never attest (ADR 0013 unchanged).
4. **The agent demo runs over the real MCP server** (stdio client from the
   `agent` extra) bridged to the Anthropic Messages API tool-use loop — a
   real LLM agent answering **only** through Tessera's seven tools. Recorded
   once locally with the maintainer's key (the M6/M7 "ran on X" pattern:
   a committed, timestamped transcript under `data/agent_session/`; CI stays
   key-free and offline).
5. **Asset split:** the agent builds the deploy-ready artifact (container
   serve mode + runbook with free-tier options), the demo script/storyboard,
   and the one-pager; the **maintainer** picks the host + deploys (spend
   decision #5) and records the 2–3-minute video. M17 tags only when the
   hosted demo is live (its "done when"), so the milestone may stay open at
   session end — reported, not fudged.
6. **Cosmetics fixed in passing:** `:trust` prints rounded numbers; the MCP
   `serverInfo.version` reports the project version, not the SDK's.

## Acceptance criteria

- [ ] **Unit 2 (spec 0113) — narration live + cosmetics:** `TESSERA_NARRATOR=anthropic`
      verified once against the real API (narration renders under its label,
      novelty guard active, refusals never narrated); `:trust` formatting; MCP
      serverInfo version; gate green, eval untouched.
- [ ] **Unit 3 (spec 0114, ADR 0027) — the web UI:** `uv run tessera-ui` serves
      one page: ask → routed answer → numbered claims with per-claim verifier
      chips → provenance drill-down (records, locators, resolution assertions
      with confidences) → refusals rendered as refusals → the action flow
      (draft → payload preview → approve → **simulated** receipt) → a trust
      panel from `eval/history.jsonl`. Every dynamic string HTML-escaped
      (evidence text is attacker-shaped in principle); rendering is pure
      functions over the trust objects, unit-tested; one socket-level smoke
      test; **focused adversarial review** (XSS/injection, trust-presentation
      honesty, docs) before merge.
- [ ] **Unit 4 (spec 0115) — the recorded agent session:** a real Claude agent,
      over the real `tessera-mcp` stdio server, grounds answers with citations,
      carries a refusal as a refusal, drafts + previews + (simulated-)executes
      a gated action — transcript committed with a MANIFEST; boundary
      contract untouched.
- [ ] **Unit 5 (spec 0116) — hosted packaging + assets:** container serve mode
      for the UI (key-free), a deploy runbook (2–3 free/cheap options), the
      3-minute demo script/storyboard (the Replit-counter-story arc), the
      one-pager (EN/DE). Deploy + video = maintainer.
- [ ] Eval floors byte-identical throughout; every unit gate-green; `/wrap`.

## Scope

**In:** exactly the four units above. **Out:** any engine/verifier change; any
new answer path; UI auth/multi-tenancy (deliberately out, ADR 0027 will record
it); the real actuator anywhere near the UI; M18 BYO connectors; the launch
motion (M19).

## Eval impact

None — the UI and demos are consumers. Narration remains outside the eval by
design (ADR 0013). Proven at each unit's gate.

## Risks / open questions

- The stdlib UI must not become a project of its own: one page, no framework
  ambitions; anything needing a new answer path is out (ROADMAP2 guard).
- XSS is the UI's B4-analogue: evidence/log text rendered into HTML. Mitigated
  by escape-everything + the focused review; pinned by hostile-content tests.
- The live narration + agent-session runs consume maintainer API credits
  (small; Haiku default for narration, Sonnet-class for the agent loop) — the
  key is in the gitignored `.env`, never committed, never in CI.
- Hosted demo depends on the maintainer's hosting decision — M17's tag waits
  for it; everything else lands regardless.
