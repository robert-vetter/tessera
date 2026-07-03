# 0027. The web surface: pure stdlib, zero JavaScript, no credential

- **Status:** accepted (Milestone 17 Unit 3, spec 0114)
- **Date:** 2026-07-03

## Context

Act 2 requires a demo a stranger can *see* (ROADMAP2 M17; the maintainer's
public Z Fellows commitment: "a live demo anyone can try"). Everything trust-
bearing already exists as serializable objects at the agent boundary —
`GroundedResult` → `ActionProposal` → `RenderedPayload` → `ExecutionReceipt`
— each measured to preserve faithfulness 1.0 (M11–M14). What was missing is a
presentation over them that a browser can render. The choice is *how* to build
that surface without weakening anything the engine promises: the default
clone-and-run has **zero runtime dependencies**, CI is offline and key-free,
and the UI will render **attacker-shaped text** (real CI logs flow through
evidence records — the audit's B4 taught this lesson at the payload renderer).

## Decision

1. **Pure stdlib.** `tessera/ui/` serves one page with `http.server`
   (`ThreadingHTTPServer`) — no framework, no pip extra, no build step. The
   rendering layer (`ui/render.py`) is pure `object → str` functions, unit-
   testable with hostile content.
2. **Zero JavaScript, strict CSP.** Server-rendered HTML + inline CSS only;
   provenance drill-down is `<details>`, the approval is a `<form>` POST.
   Every response carries `Content-Security-Policy: default-src 'none';
   style-src 'unsafe-inline'` (+ `nosniff`, `no-referrer`) — the browser is
   told to load and execute nothing, which the page makes literally true.
3. **Escape everything.** All dynamic strings pass one door
   (`html.escape`) before touching markup — the web analogue of the fence
   rule (spec 0109 B4). Pinned by hostile-content tests (script/attribute
   injection through claims, evidence, refusals, narration).
4. **The UI asserts nothing and can send nothing.** Verdict chips mirror the
   verifier's `verified` flags; refusals render as refusals; withheld
   payloads render no approve form; the action flow wires the **simulated**
   actuator only (the MCP posture, ADR 0025) — the process holds no GitHub
   credential and has no code path to the real actuator. Narration, when a
   key is configured, renders strictly below the canonical claims under the
   ADR 0013 label; a hosted, key-free instance simply has none.
5. **Stateless by construction.** Domains build once via the grounded layer's
   caches; requests share no session state; hosting it is running one
   process over committed data.

## Consequences

- A hosted demo is one container with no secrets: nothing to leak, nothing to
  send, nothing to persist. "Try it" costs the maintainer a deploy, not a
  security review.
- The zero-dependency story now extends to the product surface — a reviewer
  can read the whole UI in two files.
- Server-rendered pages mean every state is a URL: demo flows are shareable
  and the video script is a sequence of links.
- The trade-off is accepted plainness: no live search-as-you-type, no
  streaming, no client-side niceties. For a trust product, boring is a
  feature; anything needing a new answer path stays out (ROADMAP2 guard).
- Auth/multi-tenancy stay deliberately out (the demonstrator posture,
  PROJECT_BRIEF §5); a hosted instance is public read-only by design.

## Alternatives considered

- **FastAPI/Flask + templates.** Rejected: a web-framework dependency (and
  its upgrade/CVE surface) to serve one page contradicts the zero-dependency
  posture the README leads with; CI would grow a framework import for no
  measured benefit.
- **An SPA (React/HTMX-with-CDN).** Rejected: a build toolchain and/or
  external assets break the strict CSP and the offline story; the substance
  being demonstrated is server-side truth, not client-side interactivity.
- **Extending `tessera-chat` with a `--serve` flag.** Rejected: the chat
  session is an engine-level surface (business/devex only); the UI belongs on
  the *agent boundary*, where per-claim verdicts and the action arc already
  exist in serializable form for all three domains — the same objects MCP
  transports, so UI and agent surface can never drift apart.
