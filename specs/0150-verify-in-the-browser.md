# 0150. Verify in the browser — ten seconds, no install, and the file never leaves the device

- **Phase / milestone:** ROADMAP3 Milestone 22. Not a tenth guarantee — the
  unit that makes the previous nine *reachable*.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

Milestones 20–22 built receipts, chains, policies, approvals, audit
records, a measured benchmark, a machine-checked proof, a second
independent implementation and verifiable redaction. Every one of them is
real, and **every one of them lives behind `git clone` plus a toolchain.**
Nobody outside the repository has ever run any of it.

That is now the binding constraint. The artifacts do not need to be
deeper; they need to be *experienceable*. The shortest honest path from
"interesting claim" to "I just watched it happen" is a browser tab.

There is also a second, less obvious reason this belongs in this project
specifically. Tessera's central architectural claim is that verification
is **offline and local** — no service, no upload, no trust in the
operator. A verifier that runs entirely inside the visitor's browser, with
the file never leaving the device, is not a marketing page for that claim:
it *is* the claim, executed. And unlike a hosted checker, it can be
**tested** to make no network calls at all.

## Decisions

1. **Split the JavaScript verifier, do not duplicate it.**
   `verifier/js/verify-core.mjs` holds every rule — canonical bytes,
   manifest, root, section set, referential integrity, claim grammars,
   chains, redaction, approvals — with **zero imports**, so it runs
   unchanged in Node and in a browser. `verifier/js/tessera-verify.mjs`
   becomes a thin CLI wrapper (filesystem + Ed25519 via `node:crypto`).
   Two front ends, one implementation: a browser page that re-implemented
   the logic would be a *third* thing to keep correct and would prove
   nothing about the format.
2. **The core carries its own SHA-256.** Node's `crypto` is unavailable in
   a page and WebCrypto's digest is async, which would infect every
   function with `await`. A compact, dependency-free SHA-256 keeps the
   whole verifier synchronous and identical in both environments — and it
   is **differentially tested against `node:crypto`**, so the hand-written
   hash can never silently drift.
3. **Signatures are honest about the environment.** The core takes an
   optional signature-verification callback. The CLI supplies Ed25519 via
   `node:crypto`; the browser build supplies none and *says so* on any
   signed bundle rather than implying it checked. Same discipline as
   `PASS-PARTIAL` (spec 0148): never a silent gap.
4. **One generated, committed file.** `scripts/build_web_verifier.py`
   inlines the core into `docs/verify.html`; the result is committed and
   pinned byte-identical to a fresh build (the challenge/kit/certificate
   pattern). One file means it works from `file://`, from GitHub Pages,
   and from a USB stick — no build step for the user, no CDN, no
   dependency.
5. **Published where the docs already deploy.** Living under `docs/`, the
   page ships with the existing Pages workflow — a public URL with no new
   infrastructure.
6. **"Nothing leaves your device" is a pinned test, not a promise.** The
   generated page must contain no `fetch`, no `XMLHttpRequest`, no
   `WebSocket`, no form action, no external `src`/`href` to another
   origin. A test asserts it. Embedded example bundles are inlined for the
   same reason: clicking "try an example" must not become a network
   request either.
7. **The page shows the whole stack, not a toy.** Verdict, per-claim
   re-execution with the recorded-vs-re-derived comparison, chain
   upstreams (recursive), withheld items from redaction, approvals when a
   second file is dropped, and the honest "not performed here" line.
   Dropping the committed chain brief or the redacted bundle is a tour of
   Milestones 20–22 in one gesture.

## Scope

**In:** `verifier/js/verify-core.mjs`, the CLI wrapper,
`scripts/build_web_verifier.py`, `docs/verify.html` (generated, committed,
pinned), embedded example bundles, `tests/test_web_verifier.py`, docs +
README + mkdocs pointers.
**Out:** any hosted verification service (uploading defeats the point);
Ed25519 in the browser (named, honest gap); a framework, a bundler, or a
single line of CSS from a CDN.

## Acceptance criteria

- [ ] The CLI behaves exactly as before (same verdicts, same exit codes);
      the cross-implementation kit regenerates unchanged, still 0
      disagreements.
- [ ] The hand-written SHA-256 matches `node:crypto` on a differential
      battery — pinned.
- [ ] `docs/verify.html` is byte-identical to a fresh generation.
- [ ] The page contains no network API and no cross-origin reference —
      pinned by test.
- [ ] Dropping the honest example reports PASS-PARTIAL; the forged one
      reports FAIL with the broken claim named; the chain brief shows both
      upstreams; the redacted bundle shows withheld items and never a pass.
- [ ] Gate green; six eval lines byte-identical; frozen core empty-diff.

## Eval impact

None — a new front end over an existing implementation.

## Risks / notes

- **The real risk is a second implementation by accident**: a page that
  drifts from the CLI. Decision 1 (one core, two front ends) plus the
  regenerated kit make drift a build failure rather than a discovery.
- A hand-written hash is a genuine risk surface; decision 2's differential
  test is the mitigation, and the CLI keeps using `node:crypto` where it
  is available, so the two are cross-checked on every run of the harness.
