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
      `should_persist` (only `created`/`exists` are written; `exists` is the
      crash-recovery record, never a live re-run demonstration) +
      `guard_no_clobber` (an existing `receipt*.json`, matched
      case-insensitively, refuses **before any network**); the recorder
      prints-and-exits-nonzero on an approved attempt ending in any
      non-consummated outcome (`withheld`/`inconclusive`/`error` — and
      defensively `blocked`), exits non-zero on approved-but-credential-less
      invocations, and creates the receipt with exclusive-create (`"x"`). The
      policy *functions* are pinned by tests; the recorder's wiring (guard
      before actuator construction; print + `SystemExit`) is deliberate,
      untested script glue.
- [x] **B2** — the issues pre-check scans the **unfiltered** `state=all`
      listing for the exact body marker; the `idem-` label is demoted to a
      visible, non-load-bearing handle. ADR 0026 addendum records the change,
      the paging/PR-inclusion cost, and the named residuals (marker spoof —
      denial-of-create *and*, under B1, a persistable false `exists`;
      mid-scan-deletion page race; renderer-version key stability). Pinned by
      a label-independence test (`labels=` absent from the pre-check URL;
      dedup succeeds on a label-less prior issue behind a null-body PR item).
- [x] **B3** — `GithubActuator.token` is `field(repr=False)`; a test pins that
      `repr`/`str`/f-string never surface the credential (`asdict()` bypass
      noted as a guarded-against-by-convention non-use).
- [x] **B4** — fenced sections use a fence strictly longer than any backtick
      run in the value (min 3, pure function of the value); **both**
      independent reconstructions (`tests/test_payloads.py` and the CI-gated
      `tests/test_payloads_boundary.py`) implement the same declared rule; a
      hostile-content test pins no-breakout + byte-equality. Follow-on
      (review M2): a multiline value in a *non-fenced* role withholds the
      payload. ADR 0024 addendum.
- [x] **B5** — the `{pr}` segment passes `[A-Za-z0-9._-]+` (dots-only
      rejected) or the payload is withheld; parametrized hostile-id tests
      (`..`, `?`, `#`, `%2e%2e`, `/`, whitespace, empty). ADR 0024 addendum.
- [x] **Review M1** — the real transport refuses redirects (`_RefuseRedirects`):
      urllib's default handler forwards `Authorization` cross-origin and
      rewrites POST→GET, which could misreport a moved repo's listing as
      `created`; any 3xx now surfaces as `error`/`inconclusive`. Pinned by a
      handler test.
- [x] Gate green; **459 tests** (16 new); every battery number byte-identical.
      Byte-stability stated precisely: the raw logs carry single-backtick runs
      but no *fenced value* does (the excerpting drops those lines), so every
      fence degenerates to the old form; leak-guard untouched.
- [x] **Pre-merge adversarial multi-agent review** ran on the diff (5 lenses:
      recorder correctness, GitHub semantics, security, faithfulness contract,
      docs honesty; every finding independently reproduced by its reviewer).
      Outcome: 3 confirmed majors — the CI-gated boundary reconstruction still
      hardcoded the old fence (fixed: rule ported); the recorder's MANIFEST
      note promised the pre-B1 re-run behavior (fixed: reworded); the ADR 0026
      addendum misstated the original ADR's history (fixed: reworded, and the
      audit table corrected) — plus the M1/M2/M3 hardening minors and a set of
      wording/test findings, all fixed in this PR before merge. Verified
      clean by the reviewers: fence rule sufficient per CommonMark; allowlist
      complete against 31 hostile probes incl. unicode; no credential channel
      via repr/receipts/recorder; committed artifacts byte-stable.

## Scope

**In:** exactly B1–B5 + their tests + the two ADR addenda.
**Out:** B6–B8 (Unit 3 / documentation), the runbook text (Unit 4), any change
to the simulated path's behavior, the grounded slots, the renderer's
scaffolding vocabulary, or the eval.

## Eval impact

None — proven: all six battery lines byte-identical before/after (the fence
rule degenerates to the old ``` fence for every value the renderer currently
fences — the raw logs' single-backtick punycode lines never reach a fenced
field; the pre-check change affects only real-path GETs; the recorder is not
imported at runtime).

## Risks / open questions

- The unfiltered issues scan pages more on a busy repo → honest `inconclusive`
  at the cap (documented; irrelevant for the sandbox).
- The marker-spoof residual is *named*, not solved — acceptable for the
  one-shot posture (ADR 0026 addendum records the multi-tenant remedy as out
  of scope).
- `guard_no_clobber` guards only approved runs (a rehearsal writes nothing by
  construction) — keeps the rehearsal friction-free.
