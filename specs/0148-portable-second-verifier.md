# 0148. A second, independent verifier — the guarantee is the format, not my Python

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof). The
  answer to the strongest objection against everything shipped in M20–M22.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

The strongest objection to this project is not about cryptography or
method — it is about *who wrote the checker*:

> "Your benchmark is your implementation of everyone else's methods. Your
> proof is about your model. Your verifier is your Python. Every artifact
> in the chain of trust was written by the same person."

That objection is fair, and no amount of additional testing by the same
author answers it. The standard answer, and the one every real format
uses, is a **second independent implementation**: if two verifiers written
in different languages, from the format contract, agree on every case,
then the guarantee lives in the *format* rather than in one codebase.

This unit ships that: a zero-dependency verifier in JavaScript, plus a
**conformance kit** and a **differential harness** that runs both
implementations over every case and fails the build on any disagreement.

## Decisions

1. **A real second implementation, not a stub** (`verifier/js/tessera-verify.mjs`).
   Zero dependencies, Node's standard library only. It implements, from
   the format contract rather than by transliterating the Python:
   canonical JSON bytes, the leaf manifest, the Merkle root, the
   section-set commitment, the reserved-`anchor` refusal, Ed25519
   signature verification (`node:crypto`), detached approval artifacts,
   referential integrity, **claim-level semantic re-execution** (the
   generic shared-fragment and containment grammars, the business
   aggregate/compare/superlative/count/refuse grammars, and the chain
   citation grammar), and **recursive chain verification** of embedded
   upstreams.
2. **Honest scope, encoded in the verdict taxonomy.** Two checks need the
   engine itself and are therefore *not* portable: answer re-derivation
   (re-running the domain router) and action re-derivation (re-running the
   drafting pipeline). The JavaScript verifier therefore never claims a
   full PASS: its best verdict is **`PASS-PARTIAL`** — "everything this
   implementation can check passes; the answer/action re-derivation was
   not performed here." One business grammar (`conflict_disclosure`) needs
   engine-side document parsing; a claim speaking it is reported
   `NOT-EVALUABLE` rather than guessed, and that downgrades the verdict.
3. **The differential contract, tested on every case:**
   - JS `TAMPERED` ⟹ Python exit 4;
   - JS `FAIL` ⟹ Python exit 2 (or 4);
   - JS `PASS-PARTIAL` ⟹ Python exit 0 or 3 — **never** 2 or 4. This is
     the soundness direction that matters: *the portable verifier must
     never bless something the reference rejects.*
   - Per-claim verdicts must agree exactly wherever JS evaluates a claim.
4. **A conformance kit** (`data/kit/expectations.json`): every committed
   artifact (honest, forged, chain brief, an action bundle) crossed with
   the CI-pinned mutation battery, each with the expected Python exit code
   and JS verdict. Committed and pinned byte-identical to a fresh
   generation, so the published cross-implementation result cannot drift.
   Cases are *materialised deterministically at test time* from committed
   code rather than stored as files, so the kit costs bytes, not megabytes.
5. **CI runs both.** The gate job gains a Node step; a disagreement fails
   the build like any other red test.
6. **Written from the contract.** ADR 0031 (format), ADR 0032 (signing),
   ADR 0033 (chains), ADR 0035 (approvals) and `docs/BUNDLE.md` are the
   inputs. Where the JS implementation had to consult the Python to
   resolve an ambiguity, that ambiguity is a **finding about the
   specification** and is recorded in this spec's notes — an independent
   implementation is also a spec review.

## Scope

**In:** `verifier/js/tessera-verify.mjs` + its README, `data/kit/`,
`scripts/build_conformance_kit.py`, `tests/test_portable_verifier.py`,
`docs/PORTABLE.md`, README + mkdocs pointers, CI node step.
**Out:** porting the engine (router/composition) — explicitly not portable
and stated as such; a third implementation; publishing the format as an
RFC (named future work).

## Acceptance criteria

- [ ] `node verifier/js/tessera-verify.mjs data/challenge/honest.tsb` →
      `PASS-PARTIAL`; on `forged.tsb` → `FAIL` naming the broken claim.
- [ ] The chain brief verifies recursively, including the embedded
      upstreams' own claims.
- [ ] A signed bundle's signature verifies in JS; a detached approval
      checks in JS and is refused against the forged bundle.
- [ ] Every kit case: the differential contract holds; per-claim verdicts
      agree wherever JS evaluates them; **zero disagreements**.
- [ ] The committed kit is byte-identical to a fresh generation.
- [ ] Gate green; six eval lines byte-identical; frozen core, agent chain,
      bundle layer, conformance and proof packages all empty-diff.

## Eval impact

None — a new non-Python artifact plus tests and docs.

## Risks / notes

- **The honest risk is a *silent* scope gap**: a portable verifier that
  quietly skips a check would look like agreement while proving nothing.
  Mitigated by the `PASS-PARTIAL` taxonomy (it can never report a full
  pass), by per-claim verdict comparison rather than only overall
  verdicts, and by an explicit scope table in `docs/PORTABLE.md`.
- Node's `JSON.parse` is last-wins on duplicate keys while the reference
  verifier rejects them outright (spec 0134). This is a **documented
  scope difference**, not a silent one: duplicate-key files must be
  checked with the reference implementation, and the kit does not claim
  JS coverage for that case.
