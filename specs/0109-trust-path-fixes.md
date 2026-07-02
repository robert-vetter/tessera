# 0109. Milestone 16 Unit 2: trust-path fixes B1–B5

- **Phase / milestone:** Milestone 16 (Act 2 opener), Unit 2 — see spec 0107 and
  [`docs/AUDIT_2026-07-02.md`](../docs/AUDIT_2026-07-02.md) §3.
- **Issue:** —
- **Status:** implemented

## Problem

The audit's code findings concentrate in the M15 real-execution path — the one
surface that can cause a real side effect. Two directly endanger the pending
one-shot (B1 the recorder clobbers the historic receipt on re-run; B2 dedup
silently depends on the `idem-` label surviving), one leaks the credential into
any traceback (B3), and two let hostile *content* shape a real request (B4
fence injection into a created issue; B5 malformed `{pr}` ids into the URL
path). All five are fixed before the one-shot may run.

## Acceptance criteria

- [x] **B1** — persistence policy moved into the tested `agent/recording.py`:
      `should_persist` (only `created`/`exists` are written) +
      `guard_no_clobber` (an existing `receipt*.json` refuses **before any
      network**); the recorder prints-and-exits-nonzero on an approved attempt
      ending `blocked`/`inconclusive`/`error`. Pinned by tests.
- [x] **B2** — the issues pre-check scans the **unfiltered** `state=all`
      listing for the exact body marker; the `idem-` label is demoted to a
      visible, non-load-bearing handle. ADR 0026 addendum records the change,
      the paging cost, and the (now named) marker-spoof denial-of-create
      residual. Pinned by a label-independence test (`labels=` absent from the
      pre-check URL; dedup succeeds on a label-less prior issue).
- [x] **B3** — `GithubActuator.token` is `field(repr=False)`; a test pins that
      `repr`/`str`/f-string never surface the credential.
- [x] **B4** — fenced sections use a fence strictly longer than any backtick
      run in the value (min 3, pure function of the value); the boundary
      test's *independent* reconstruction implements the same declared rule;
      a hostile-content test pins no-breakout + byte-equality. ADR 0024
      addendum.
- [x] **B5** — the `{pr}` segment passes `[A-Za-z0-9._-]+` (dots-only
      rejected) or the payload is withheld; parametrized hostile-id tests
      (`..`, `?`, `#`, `%2e%2e`, `/`, whitespace, empty). ADR 0024 addendum.
- [x] Gate green; **456 tests** (13 new); every battery number byte-identical
      (fences unchanged on the current corpus — no value carries a backtick
      run); leak-guard untouched.
- [x] **Pre-merge adversarial multi-agent review** on the diff (side-effect-
      capable surface), findings triaged and confirmed ones fixed before merge.

## Scope

**In:** exactly B1–B5 + their tests + the two ADR addenda.
**Out:** B6–B8 (Unit 3 / documentation), the runbook text (Unit 4), any change
to the simulated path's behavior, the grounded slots, the renderer's
scaffolding vocabulary, or the eval.

## Eval impact

None — proven: all six battery lines byte-identical before/after (the fence
rule degenerates to the old ``` fence for every current value; the pre-check
change affects only real-path GETs; the recorder is not imported at runtime).

## Risks / open questions

- The unfiltered issues scan pages more on a busy repo → honest `inconclusive`
  at the cap (documented; irrelevant for the sandbox).
- The marker-spoof residual is *named*, not solved — acceptable for the
  one-shot posture (ADR 0026 addendum records the multi-tenant remedy as out
  of scope).
- `guard_no_clobber` guards only approved runs (a rehearsal writes nothing by
  construction) — keeps the rehearsal friction-free.
