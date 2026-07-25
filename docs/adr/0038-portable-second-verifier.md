# 0038. A second implementation, and an honest `PASS-PARTIAL`

- **Status:** accepted (2026-07-18, spec 0148)
- **Context:** ROADMAP3 Milestone 22 — answering the one objection that
  no additional work by the same author can answer.

## Context

By Milestone 22 the project could show a measured comparison
(CONFORMANCE.md) and a machine-checked theorem (PROOF.md). Both are
strong; both share an author with the verifier they describe. The
remaining objection is structural:

> Your benchmark is your implementation of everyone else's methods, your
> proof is about your model, and your verifier is your Python.

The standard answer — the one every durable format uses — is an
independent implementation. If two verifiers written in different
languages, from the format contract, agree on every case, the guarantee
lives in the *format*, not in one codebase.

## Decision

Ship a **second verifier in JavaScript** (`verifier/js/tessera-verify.mjs`,
zero dependencies, Node standard library only), a **conformance kit**
(`data/kit/expectations.json`), and a **differential harness** that runs
both over every case in CI.

1. **Honest scope encoded in the verdict, not in a footnote.** Two checks
   need the engine and cannot be ported: answer re-derivation (re-running
   the domain router) and action re-derivation (re-running the drafting
   pipeline). The portable verifier therefore **cannot report a full
   PASS** — its best verdict is `PASS-PARTIAL`, and its output always
   prints what it did not do. A claim speaking a grammar it does not carry
   is `NOT-EVALUABLE`, never guessed.
2. **The differential contract is asymmetric, on purpose.**
   - `TAMPERED` ⟹ the reference exits 4.
   - `FAIL` ⟹ the reference exits 2 or 4 — *the portable verifier never
     rejects what the reference accepts*.
   - `PASS-PARTIAL` alongside a reference failure is allowed **only** when
     every named reference cause is one of the two non-portable checks.
     That is verified per case against the reference's own problem
     strings, not asserted in prose.
   Measured over the kit: 25 cases, **12 caught by both**, **7 declined by
   design**, 6 honest baselines passing in both, **0 disagreements**.
3. **Written from the contract, and therefore a specification review.**
   Where the second implementation could not reproduce a result from the
   documents alone, the ambiguity is a defect in the *specification*, to
   be fixed there. One such defect was found immediately and is recorded
   in the ADR 0031 addendum: `tessera-canonical-json-1` was
   under-specified for numbers.
4. **The kit is generated, not stored.** Cases are materialised
   deterministically from committed code (the committed artifacts crossed
   with the CI-pinned attack battery), so the kit costs kilobytes and can
   never drift from the generators it describes; the expectations file is
   pinned byte-identical to a fresh run.

## Alternatives rejected

- **A stub or a partial port that reports PASS.** It would produce the
  appearance of agreement while proving nothing — the exact failure mode
  this unit exists to remove. `PASS-PARTIAL` is the honest ceiling.
- **Transliterating the Python.** A translation shares the original's
  misunderstandings and cannot review the specification. Writing from the
  contract is what surfaced the canonicalisation defect.
- **Porting the engine too.** Router and composition are thousands of
  lines of vertical logic; a port would be a second engine to keep
  correct, and its divergence would say nothing about the *format*.
- **Depending on a JSON-canonicalisation library.** The dependency-free
  property is the point: a stranger runs `node tessera-verify.mjs` with
  nothing installed.

## Consequences

- The trust story stops resting on one codebase: two implementations, two
  languages, one format, agreeing case by case in CI.
- The scope table in `docs/PORTABLE.md` is now load-bearing documentation
  — if the declined set ever grows, a test fails.
- Future format changes must be implementable from the written contract,
  or they are not finished; the second implementation is the check on
  that.
- A third implementation (Rust/Go) and publishing the format as an RFC are
  natural next steps, named rather than promised.
