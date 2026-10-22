# 0147. The bounded soundness theorem — from "we tested attacks" to "no false PASS exists"

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof). The
  strongest trust-bearing claim the project has ever made, so the
  honesty rules are the strictest yet: every word of the theorem
  statement is bounded, and what is *not* proven is stated in the same
  breath as what is.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

Everything the project claims about its verifier is, today, **empirical**:
a 16-class mutation battery at 100% detection (spec 0137), a 21-attack
conformance benchmark (spec 0146), an adversarially-reviewed
implementation. All of it says *"we tried these attacks and none got
through."* None of it says *"no attack can get through."*

That is the difference between testing and proof, and it is the last
categorical step available. This unit takes it, honestly and within a
stated bound: **enumerate every possible bundle state in a bounded
universe — not a sample, all of them — and machine-check that every state
the verifier PASSes is in fact honest.**

The property is exactly the one the entire product rests on:

> **Soundness (bounded).** For every state `S` in the universe `U(R, V, C)`:
> `verify(S) = PASS ⟹ S is honest`, where *honest* means every claim's
> asserted content is derivable from the evidence it cites, every
> recorded verdict equals the recomputed one, and the recorded answer is
> exactly the one the packaged corpus yields for the packaged question.

Because the universe is closed under arbitrary edits, an attacker — with
unlimited re-sealing, re-signing, and re-writing power — can only ever
produce a state that is already in `U`. So the theorem covers *every
possible forgery in the bounded domain*, including ones nobody has
thought of. That is the difference from a mutation battery.

## Decisions

1. **Exhaustive enumeration, not reachability.** Rather than "apply k
   attacker edits and check", the checker enumerates the whole universe
   and checks the implication for every state. This removes the need to
   argue that an edit algebra is complete: the universe *is* the closure
   of every edit sequence, so attacker-reachability follows as a
   corollary. Stronger and simpler to audit.
2. **The model mirrors the shipping verifier's PASS conditions exactly**
   (`tessera/proof/model.py`): a state passes iff (a) every claim's
   recorded verdict equals its recomputed verdict *and* both are true —
   which is precisely the real `exit_code == 0` condition after
   `semantic_problems` and `degraded` — and (b) the recorded claim set
   equals the canonical answer for the packaged question over the
   packaged corpus (the real check (b), answer re-derivation).
3. **A differential fidelity bridge to the real code**
   (`tessera/proof/bridge.py`). Model claim validity is not asserted to
   match the implementation — it is **checked against the shipping
   verifier itself**: every model claim in the universe is materialised
   into real `EvidenceRecord`/`Node`/`Claim` objects and evaluated by the
   real `is_supported` with the real `BUSINESS_CLAIM_SHAPES`. Any
   disagreement fails the build. This is the honest link between a proof
   about a model and a claim about the product.
4. **Negative controls are mandatory** (`tessera/proof/check.py`). The
   checker must be *able* to find unsoundness, or "PROVED" means nothing.
   Two deliberately flawed verifiers are checked in the same run:
   - `trusting` — believes the recorded verdict instead of recomputing
     it (this is exactly what an integrity-only receipt does);
   - `claims-only` — recomputes claims but skips answer re-derivation.
   Both **must** yield concrete counterexamples, and the certificate
   prints them. A run where a negative control comes back "proved" is a
   failed run, not a good one.
5. **The bound is stated everywhere the result is.** Universe A (single
   claim, ≤3 records, values 1–4) and Universe B (two claims, ≤2
   records, values 1–3) are enumerated in full; the exact state counts
   are printed and committed. The claim is never "formally verified",
   always "exhaustively machine-checked over a bounded domain".
6. **`tessera proof [--json] [--deep]`**; the certificate is committed at
   `data/proof/certificate.json` and pinned byte-identical to a fresh run
   (the scorecard/challenge pattern), so a published theorem can never
   drift from the code that produced it.
7. **Pure stdlib, offline, deterministic.** No SMT solver, no external
   dependency: exhaustive enumeration over a finite domain *is* a
   decision procedure, and keeping it dependency-free means a reviewer
   can audit the whole proof in one file.

## What this does NOT prove (stated in the docs, verbatim)

- It is **not** a proof about the Python implementation. It proves a
  property of a model whose *claim semantics* are differentially pinned
  to the shipping verifier over the same domain; hashing, JSON handling,
  I/O and the rest of the implementation are out of scope.
- It is **bounded**: 1–2 claims, ≤3 records, small value domains. Larger
  states are not covered; the bound is printed with every result.
- It says nothing about truth in the world — the same scope limit the
  whole project carries.
- Model fidelity is **tested, not proven** (that gap is inherent to this
  technique and is named rather than glossed).

## Scope

**In:** `tessera/proof/{model,universe,bridge,check,cli}.py`, the `proof`
CLI verb, `data/proof/certificate.json`, `tests/test_proof.py`,
`docs/PROOF.md`, README + mkdocs pointers, a CONFORMANCE.md cross-link
(the benchmark measured the gap; the proof shows one side cannot have it).
**Out:** verification of the implementation itself; SMT/proof-assistant
formalisation (named future work); unbounded claims of any kind.

## Acceptance criteria

- [ ] `tessera proof` enumerates both universes in full, prints the exact
      state counts, and reports PROVED for the real verifier model.
- [ ] Both negative controls report REFUTED with a concrete, printed
      counterexample — pinned by tests (a checker that cannot fail is
      worthless).
- [ ] The fidelity bridge checks every distinct model claim against the
      real `is_supported` with zero disagreements — pinned.
- [ ] The committed certificate is byte-identical to a fresh run.
- [ ] Deterministic across `PYTHONHASHSEED`; stdlib-only; no network.
- [ ] Gate green; six eval lines byte-identical; frozen core, agent chain
      and bundle layer empty-diff; mkdocs strict green.

## Eval impact

None — additive package + CLI + docs + tests.

## Risks / notes

- **Overclaim is the entire risk of this unit.** Mitigations: the word
  "bounded" in the theorem name, the state counts printed with every
  result, an explicit "what this does not prove" section in the docs and
  in the CLI output, and the negative controls that make PROVED
  falsifiable.
- If the fidelity bridge finds a disagreement, that is a **finding about
  the implementation or the model**, to be recorded and fixed — not
  worked around by weakening the model.
