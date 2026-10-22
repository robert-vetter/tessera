# 0040. One core, two front ends — and a verifier that runs in a tab

- **Status:** accepted (2026-07-18, spec 0150)
- **Context:** ROADMAP3 Milestone 22 — after nine guarantees, the binding
  constraint stopped being depth and became reach.

## Context

Milestones 20–22 produced receipts, chains, policies, approvals, audit
records, a measured benchmark, a machine-checked proof, an independent
second implementation and verifiable redaction. Every one is real; every
one requires `git clone` plus a toolchain. Nobody outside the repository
had ever run any of it.

There is also a substantive reason a browser build belongs to *this*
project rather than being marketing: Tessera's central architectural claim
is that verification is offline and local — no service, no upload, no
trust in the operator. A page that verifies entirely on the visitor's
device is that claim executed, and unlike a hosted checker it can be
**tested** to make no network calls at all.

## Decision

1. **Split, never duplicate.** `verifier/js/verify-core.mjs` holds every
   rule with **zero imports**, so the identical file runs behind the CLI
   and inside a page. `tessera-verify.mjs` becomes a thin wrapper
   (filesystem, Ed25519, rendering, exit codes). A page that
   re-implemented the rules would be a *third* implementation to keep
   correct and would prove nothing about the format.
2. **The core carries its own SHA-256.** Node's crypto is absent in a
   browser and WebCrypto's digest is async, which would make every
   function async. A compact dependency-free hash keeps the verifier
   synchronous and identical in both environments — and it is
   **differentially tested against `node:crypto`**, so a hand-written hash
   cannot drift.
3. **Signatures are honest about the environment.** The core takes an
   injected Ed25519 verifier. The CLI supplies one; the browser build does
   not and *says so* when it meets a signed bundle. Same rule as
   `PASS-PARTIAL`: never a silent gap.
4. **Generated, committed, pinned.** `scripts/build_web_verifier.py`
   inlines the core and two example bundles into `docs/verify.html`; the
   committed file is pinned byte-identical to a fresh build, so the page
   cannot drift from the verifier it runs. The markup lives in
   `verifier/web/template.html` as real HTML.
5. **"Nothing leaves your device" is a test.** The generated page must
   contain no `fetch`, `XMLHttpRequest`, `WebSocket`, `sendBeacon`,
   `EventSource`, dynamic `import()`, `<form>`, `<iframe>`, `<img>` or
   `action=`, and no URL anywhere outside the inert example data. A trust
   tool should not have to be believed.
6. **Published where the docs already deploy** — under `docs/`, so the
   existing Pages workflow serves it with no new infrastructure.

## Alternatives rejected

- **A hosted verification service.** Uploading the file to check it
  destroys the property being demonstrated, and adds infrastructure whose
  operator must then be trusted.
- **A hand-written page next to the CLI.** Two copies of the rules, drift
  guaranteed, and the agreement between them would mean nothing.
- **WebCrypto for hashing.** Async digests would infect the entire
  verifier with `await` for no benefit, and the resulting code would no
  longer be the same code the CLI runs.
- **A bundler or framework.** The value here is that the artifact is one
  file a stranger can read, save, and run offline.

## Consequences

- The nine guarantees became reachable in ten seconds by anyone with a
  browser, and the demo works with the network switched off.
- The core is now the single source of truth for three surfaces (CLI,
  page, cross-implementation kit); a change that breaks one breaks the
  build.
- Ed25519 in the browser is a named, honest gap — the natural next step if
  a signed bundle ever needs checking without a terminal.
