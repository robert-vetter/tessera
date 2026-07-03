# 0121. "Pilot in a day" runbook

- **Phase / milestone:** Milestone 18 Unit 5 (spec 0117 decision 8). The
  design-partner vehicle: a runbook that takes a stranger from a clean clone to
  a grounded, provenance-complete answer **on their own data in under 30
  minutes** — the consultancy offer made concrete. Docs-only.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Units 2–4 built the two BYO doors; a pilot needs a single page that strings
them into an offer: prerequisites, the exact commands, what the client keeps
(the audit artifact), and the honest limits. Without it the capability is real
but not *sellable* — the ROADMAP2 M18.3 wedge from demo to product.

**Recorded decisions:**

1. **`docs/PILOT.md`**, in the mkdocs nav, with pointers from README and
   `docs/DEMO.md`. Two paths: A = a public GitHub repo's CI failures
   (connect → ask → smoke); B = the client's CSV + Markdown (ingest → ask).
2. **The success criterion is measured and stated**: a stranger reaches a
   grounded, provenance-complete answer on their own repo in <30 minutes from
   clone. The mechanical part (connect + ask on a fresh repo) is ~20 seconds
   (measured on a third repo, mkdocs/mkdocs); the budget is dominated by
   `uv sync` + reading, so <30 minutes holds with wide margin.
3. **The honest limits are first-class**, not a footnote: snapshot-not-live,
   foreign-data-stays-local (generality claimed only for the two measured
   corpora), the recurrence weak-signal caveat, and no-LLM-in-the-trust-path.

## Acceptance criteria

- [ ] `docs/PILOT.md` covers prerequisites, both command paths (verbatim,
      copy-pasteable), the audit artifact the client keeps, and the honest
      limits — in mkdocs nav; README + `docs/DEMO.md` point to it.
- [ ] The <30-minutes-from-clone success criterion is stated with the measured
      mechanical timing behind it.
- [ ] `mkdocs build --strict` green; gate green; no code change (six eval
      lines byte-identical by construction).

## Scope

**In:** `docs/PILOT.md`, mkdocs nav entry, README + DEMO pointers. **Out:** any
code change; the launch motion (M19); the SAP track.

## Eval impact

None — documentation only.

## Risks / open questions

- The runbook must not overclaim: it states the measured scope (two repos +
  one committed corpus), the snapshot/limits, and points to `smoke` as the
  per-repo honesty check rather than asserting universal correctness.
