# 0029. Root-cause hypotheses + the generic shared-fragment claim shape

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 4
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded here)

## Problem

The DevEx milestone behaviour: *"why did this pipeline fail, and has it
happened before?"* — answered with claims grounded in log lines and linked
to prior incidents. The valuable part ("this same failure occurred in an
earlier run / a documented incident") asserts that one evidence fragment
occurs across several distinct sources, which **no existing verifier shape
can check** (ADR 0008 finding #1). The fix must not put DevEx vocabulary in
eval internals.

## Acceptance criteria

- [ ] `eval/metrics.py` gains exactly one new, vertical-neutral shape —
      **shared-fragment**: a claim of the grammar
      `… "FRAGMENT" appears in 'SRC_A' and 'SRC_B'[…]` is supported iff
      (a) it cites ≥ 2 records, (b) the sources named *after* `appears in`
      equal *exactly* the cited records' `origin.source` set (parsing the
      tail only, so quotes inside the fragment cannot masquerade as
      sources), and (c) the quoted fragment appears (normalized) in
      **every** cited record. Adversarially
      tested with vertical-free fixtures: a fabricated recurrence (fragment
      absent from one citation), an unnamed cited source, a named uncited
      source, and a single-citation claim are all caught.
- [ ] `tessera/devex/rca.py` — `explain_failure(question, graph)`:
      run-row claim + error-chunk claims (verbatim snippets), a
      **recurrence claim** (shared-fragment grammar) when the extracted
      error signature appears in an *earlier* run's log, and a
      **documented-incident claim** + ticket snippet when a ticket quotes
      the signature. Refusals with reasons: no run named, unknown run, and
      — premise rejection — the run *passed*.
- [ ] Every emitted claim passes `is_supported` (pre-checked in tests, so
      Unit 8's battery cannot be surprised).
- [ ] First-occurrence honesty: the *first* failed run of a signature gets
      no recurrence claim (nothing prior); single-occurrence failures
      (R-1018, R-1012) get neither recurrence nor incident claims.

## Scope

**In:** the one verifier shape (ADR 0008 sanctioned delta #1), the RCA path,
tests for both.
**Out:** change-summaries (Unit 5), routing/CLI (Unit 6), commit/PR blame
("which change broke it" — future work; the corpus supports it via PR-188 ↔
R-1018, deliberately left for a later phase), any other core change.

## Eval impact

None yet (no battery consumes this until Unit 8). The new shape widens what
*can* be verified; it cannot relax any existing verdict because its grammar
matches no existing claim text.

## Risks / open questions

- Signature extraction is a deliberate, simple rule recorded here: the first
  log line matching `ERROR <token>: <signature>` in the failed run's error
  chunks; the colon requirement excludes the `ERROR job … failed` trailer.
- "Has it happened before" means *earlier `started` timestamp*, compared as
  ISO strings — deterministic, no clock.
