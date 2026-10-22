# 0036. Grading verification *methods*, under two named threat models

- **Status:** accepted (2026-07-18, spec 0146)
- **Context:** ROADMAP3 Milestone 22 — converting the project's central
  positioning claim ("integrity is solved; content is not checked") from
  an assertion into a re-runnable measurement, without becoming the kind
  of vendor benchmark nobody believes.

## Context

Every comparative benchmark published by a vendor has the same defect:
the author wins. The reader cannot tell whether the baselines were
implemented to lose. Since Tessera's entire pitch rests on a comparative
claim, the benchmark had to be designed so that a hostile reader can
check it — and so that the honest cases where the alternatives are
*sufficient* appear in the results rather than being suppressed.

## Decision

1. **Grade methods, never products.** The suite contains our own,
   committed, steelmanned implementations of the *published verification
   methods* of 2026 (hash-chained receipts; signed receipts per the IETF
   ASQAV draft; policy/covenant-bound receipts per Microsoft's Agent
   Governance Toolkit proposal; PoE-style syntactic validator invariants
   per arXiv:2607.05397) plus Tessera's re-execution. No third-party
   product is run, named in a score, or characterized beyond what its own
   published description says about itself.
2. **Two threat models, T1 stated first.**
   - *T1 (outside tamperer)*: the attacker cannot produce the issuer's
     attestation. Signature-based methods detect **everything**, and the
     report says so before it says anything else. Under T1 Tessera's
     re-execution adds no detection power — recorded, not hidden.
   - *T2 (the issuer)*: the forgery is created inside the trust boundary
     and re-signed with a legitimate key. This is the operative model for
     an AI agent's own receipt, because the issuer is the party whose
     honesty is in question. Under T2 every non-re-executing method is
     blind to semantic edits **by construction**, not by weak
     implementation.
3. **Three outcomes.** `DETECTED` / `MISSED` / `NOT-APPLICABLE`. The
   third exists so that an attack impossible against a design (an
   in-artifact policy swap against a design that keeps policy outside the
   artifact) is not scored as a win. `NOT-APPLICABLE` never counts toward
   a score.
4. **Anti-strawman invariants are tests, not promises.** Each reference
   method must detect 100% of the attack family it was designed for, and
   the T1 sweep must be perfect for the signature-based methods. If a
   future edit weakens a baseline, the build fails.
5. **The scorecard is a committed artifact, pinned byte-identical** to a
   fresh run (the challenge-artifact pattern), so a published number can
   never drift away from the code that produced it.

## Alternatives rejected

- **Benchmarking named products.** Not defensible solo: it would require
  running vendor software under configurations we cannot verify, and any
  error becomes a false public statement about a real company.
- **A single "score".** A scalar hides the structure. The interesting
  result is *which family* each method is blind to, and a per-family
  table shows it.
- **Only the T2 model** (the flattering one). It would have produced a
  table where the alternatives score near zero everywhere — technically
  reproducible, rhetorically dishonest, and easy for a sharp reader to
  dismantle. T1 belongs in the report because it is true.
- **Folding this into the existing faithfulness benchmark.** Different
  question (does *this engine* answer faithfully vs. what can *a method*
  detect), different failure modes; conflating them would blur both.

## Consequences

- The project's public claim becomes checkable in one command, and its
  own limits become part of the published artifact.
- The prior-art reading (especially PoE) forces a more precise public
  claim: Tessera re-executes *claim-vs-evidence*, which is a different
  axis from execution attestation/replay. Adjacent work is credited.
- Adding a method or an attack is additive; the pinned scorecard makes
  every change to the published numbers visible in review.
