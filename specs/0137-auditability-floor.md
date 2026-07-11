# 0137. The Auditability Floor — the measured, CI-pinned artifact

- **Phase / milestone:** ROADMAP3 Milestone 21, unit 3 (plan: spec 0131).
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0131).

## Problem

The bundle machinery works, but the act needs what the Faithfulness
Floor gave Milestone 19: a **measured artifact that can fail** — a
standing, CI-pinned number a reviewer can trust and an attacker can try
to break. This unit ships the **Auditability Floor**: a runner that
proves, on every commit, that (a) every gold-case bundle re-derives to
the same verdicts from the file alone, and (b) a battery of deliberate
tampers is caught 100% with the correct cause named. It mirrors the
Faithfulness Floor's shape (spec 0122, `eval/benchmark.py`): a generated,
byte-pinned doc block plus tests that fail if a floor slips.

## Decisions

1. **Two floors, both 100%, both able to fail.**
   - **Re-derivation equality — floor 100%.** For every gold case of all
     three committed batteries, emit a bundle, verify it offline in a
     subprocess (a genuinely separate interpreter — the strongest form
     of "a stranger re-runs it"), and require exit 0 with verdict PASS.
     Milestone 20 pins this in-process; this unit adds the
     out-of-process, artifact-backed version.
   - **Mutation detection — floor 100%.** A deterministic mutation
     battery over a representative bundle (answer + action): each mutant
     must produce the correct non-PASS class **and** name the broken
     claim/link. Every mutant re-seals where that is the realistic
     attack, so the battery tests the semantic layer, not just the hash.
2. **The mutation battery (≥12 classes), each a named generator:**
   evidence value edit · evidence record omission (dangling cite) ·
   claim text edit · recorded verdict flip · answer question swap ·
   refusal-reason edit · closure-kind downgrade · fabricated
   `locator.render` · leaf reorder · root mismatch · signature mismatch
   (skipped without the `sign` extra) · engine-version spoof · wire-slot
   value injection (action) · wire-body divergence (action) · ghost slot
   provenance (action). Each generator returns `(mutant, expected_class,
   expected_substring)`; the runner asserts the verdict class and that
   the named cause contains the substring. Classes map to the taxonomy
   /exit codes (spec 0134/0136): TAMPERED(4), FAIL(2), DEGRADED(3).
3. **`eval/auditability.py` + `tessera-auditability` console script.**
   Computes both floors and prints a report; `--emit-doc` regenerates
   the pinned block in `docs/AUDITABILITY.md` (the BENCHMARK.md pattern).
   The generated block carries: the equality count (N gold cases, all
   PASS), the mutation table (class → detected? → exit), the OS/Python
   the run observed, and measured bundle sizes.
4. **`bundle/mutations.py`** holds the deterministic generators (pure
   functions `dict -> dict`), reused by both `eval/auditability.py` and
   the tests — one source of truth for "what a tamper looks like".
5. **CI: a bundle-determinism matrix job.** A new `.github/workflows`
   job (or a matrix on the existing gate) runs **only the bundle test
   subset** on ubuntu/macos/windows × Python 3.12/3.13, asserting
   byte-identical emission and 100% re-derivation across platforms —
   the guard that one spurious mismatch on a stranger's laptop can't
   sink the claim. The main single-job gate is unchanged; the matrix is
   additive and scoped (fast). Windows line-endings and filesystem
   ordering are explicitly in scope.
6. **Pinning, the honest way.** `docs/AUDITABILITY.md`'s generated block
   is byte-pinned by a test (regenerate-and-compare, like BENCHMARK.md);
   the two floors are pinned as strict equalities (100%, not "≥"). A
   floor that slips fails the gate — the number cannot quietly decay.
   The doc names exactly what each floor does and does **not** prove
   (re-derivability and tamper-detection on the committed corpora; not a
   claim about arbitrary external data), scoped by spec 0131's caveats.

## Scope

**In:** `bundle/mutations.py`, `eval/auditability.py` + console script,
`docs/AUDITABILITY.md` (generated block + prose) + mkdocs nav, the CI
matrix job, `tests/test_auditability.py` (+ doc byte-pin).
**Out:** Rekor (0138), compliance mapping (0139), the challenge (0140),
new verification logic (this unit measures the existing verifier, it
does not change it).

## Acceptance criteria

- [ ] `tessera-auditability` reports equality 100% (all gold cases, all
      three batteries, PASS out-of-process) and detection 100% (every
      mutation class caught with the right class + named cause).
- [ ] `docs/AUDITABILITY.md` generated block is byte-pinned; regenerating
      it is a no-op on a clean tree.
- [ ] Both floors are strict-equality pinned in tests and fail the gate
      if slipped (a deliberately weakened verifier makes a mutation test
      go red — proven with a temporary local edit, then reverted).
- [ ] The CI matrix job is green on all three OSes; emission is
      byte-identical across them.
- [ ] Gate green; six eval lines byte-identical; the Faithfulness Floor
      is untouched; the frozen core is untouched (empty-diff audit at
      the milestone close).

## Eval impact

Adds two **new** pinned floors (auditability), independent of the six
faithfulness eval lines, which stay byte-identical. If any existing
metric moves, the change is wrong.

## Risks / notes

- The mutation battery must exercise a bundle that has BOTH an answer
  and an action, so the action mutation classes are reachable; the
  representative bundle is a devex incident bundle (grounded, multi-slot).
- Cross-platform determinism is the real risk; it is precisely what the
  matrix exists to catch, and the data model (strings + Decimal, sorted
  canonical JSON) is already byte-stable across processes (pinned since
  unit 0133).
- The signature-mutation class needs the `sign` extra; it is skipped
  cleanly where absent (like the signing tests) and the doc block notes
  when it was not measured.
