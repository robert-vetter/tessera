# 0037. Proving soundness by exhaustive enumeration, with mandatory negative controls

- **Status:** accepted (2026-07-18, spec 0147)
- **Context:** ROADMAP3 Milestone 22 — the last categorical step available
  to this project: from *"we tested these attacks and none got through"*
  to *"no attack in this domain can get through"*.

## Context

Every guarantee the project publishes is empirical: a 16-class mutation
battery, a 21-attack conformance benchmark, adversarial review. Those
answer "did any of the attacks we thought of succeed?" They cannot answer
"could an attack we did not think of succeed?" — which is the question a
serious buyer, and an honest engineer, actually has.

The obstacle is that the shipping verifier is Python: verifying it
directly would need a proof assistant and a formalisation of the language,
which is not a solo-scope project and would be dishonest to promise.

## Decision

Prove the property of a **small model** whose fidelity to the code is
itself machine-checked, by **exhaustive enumeration over a bounded
universe**, with **mandatory negative controls**.

1. **Enumerate the universe, not attack paths.** The checker walks every
   state in `U(records, values, claims)` and checks
   `PASS(S) ⟹ honest(S)`. Because `U` is closed under arbitrary
   rewriting, an attacker with unlimited re-seal and re-sign power can
   only produce states already in `U`; attacker coverage therefore follows
   as a corollary and no completeness argument about an edit algebra is
   required. Exhaustive enumeration over a finite domain *is* a decision
   procedure, so the result is a proof for that domain — no SMT solver, no
   dependency, auditable by reading.
2. **The model gives the attacker maximum power:** it contains no hashes
   and no signatures at all. Everything an attacker could re-seal is
   assumed already re-sealed, so states are judged purely on whether their
   content hangs together. This is the conformance benchmark's *issuer*
   threat model taken to its limit.
3. **Fidelity is differential, not asserted.** Every model claim is
   materialised into real `EvidenceRecord`/`Node`/`Claim` objects and
   evaluated by the shipping `is_supported` with the real business claim
   shapes. A disagreement fails the build and is a finding about the model
   or the implementation — never something to work around by weakening
   the model.
4. **Negative controls are part of the theorem, not an extra.** Two
   deliberately unsound verifiers — one that trusts the recorded verdict
   (exactly what an integrity-only receipt does), one that recomputes
   claims but never re-derives the answer — are checked in the same run
   and **must** be refuted with printed counterexamples. `proved` is
   defined to require both refutations, so a checker that lost its ability
   to detect unsoundness reports NOT PROVED rather than a vacuous success.
5. **The bound travels with the claim.** Universe sizes are computed by
   formula *and* by enumeration, and the run fails if they disagree (an
   enumeration that silently skipped states would make the theorem
   vacuous). Every rendering prints the bounds and a "what this does not
   prove" section.

## Alternatives rejected

- **A proof assistant (Coq/Lean/Isabelle) over the real code.** The
  honest version needs a formalised Python semantics; the dishonest
  version proves a hand-written spec and calls the product verified.
  Named as future work, not promised.
- **SMT/symbolic model checking (Z3).** Adds a heavyweight dependency to
  a project whose selling point is a dependency-free verifier, and buys
  little at these bounds: the domain is finite and small enough that
  enumeration is both complete and fast (~1 s).
- **Property-based testing (Hypothesis).** Samples; would let the project
  say "we tried very hard", which it can already say. The step being taken
  here is precisely the one from sampling to exhaustion.
- **Skipping the controls.** Then "PROVED" would be unfalsifiable output
  from code nobody can audit for correctness. The controls are what make
  the word mean anything.

## Consequences

- The project can state a *proof*, correctly bounded, and the bound is
  never separable from the statement.
- Widening a bound is a one-line change with a visible cost in the
  certificate, so the claim can grow with evidence rather than with
  rhetoric.
- If the fidelity bridge ever disagrees, the build fails — the model
  cannot silently drift away from the verifier it describes.
- The certificate is a committed artifact pinned byte-identical to a fresh
  run, like the conformance scorecard and the challenge bundles.
