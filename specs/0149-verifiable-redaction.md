# 0149. Verifiable redaction — send the receipt without sending the data

- **Phase / milestone:** ROADMAP3 Milestone 22. Trust-bearing and
  adversarially reviewed: redaction touches what a verdict *means*.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

Every layer shipped so far assumes the receipt can be handed over. In a
real enterprise it usually cannot: a trust bundle packages the **whole
evidence closure** — customer master data, log lines, ticket text — so
sharing a decision means sharing the corpus it was decided on. Legal,
privacy and commercial reality say no. The result is that the strongest
artifact this project produces stays inside the building, which is the
quietest possible adoption blocker.

Verifiable credentials solved the analogous problem with *selective
disclosure*. This unit brings it to evidence bundles:

> **Withhold evidence without losing verifiability — and without moving
> the root.** A redacted bundle keeps the integrity manifest it was sealed
> with; every withheld record contributes the commitment (its original
> leaf digest) instead of its content. The root recomputes **bit-for-bit
> identical**, so a signature or a detached approval made over the
> original still verifies over the redacted copy — and the auditor sees
> exactly which evidence was withheld and which claims that costs.

## The load-bearing safety property

> **Redaction can hide, but it can never upgrade a verdict.**

A claim citing withheld evidence is not "still verified" — it becomes
**not re-derivable here**, reported per claim, and the bundle can never
report a full PASS again. Concretely: taking the forged challenge bundle
and redacting the evidence that exposes it must **not** turn FAIL into
PASS; it degrades instead. This is the adversarial pin the whole unit
rests on, and it is tested directly.

## Decisions

1. **Leaf-level commitments, manifest untouched** (`format.py`). A
   redacted graph node becomes `{"redacted": true, "record": {"id": …}}`;
   a redacted whole section becomes `{"redacted": true}`. When computing
   the manifest, a redacted item contributes the value already stored in
   `integrity.leaves` for its leaf name — so the manifest and root are
   preserved exactly. The record **id is kept**, because citations and
   referential integrity must still resolve; the docs state that ids
   remain visible.
2. **Format minor 1.2 as a per-file feature level** (the chain precedent):
   a redacted bundle declares 1.2, everything else keeps declaring what it
   declared, so committed artifacts stay byte-stable.
3. **A redacted bundle never reports PASS.** Verification treats a claim
   citing a withheld record as *not re-derivable* rather than as a
   mismatch (a mismatch would wrongly read as a lie), lists it, and forces
   the degraded path (exit 3). The verdict line names the redaction.
4. **`result` is never redacted in v1.** The claims and their inline
   support are the finding being shared; the corpus is what must stay
   home. Redacting the finding would leave nothing to verify. Stated as a
   documented limit: *evidence a claim cites is visible in the claim's own
   support; if that cannot be shared, the receipt cannot be shared.* What
   redaction removes is the far larger **uncited** corpus.
5. **A useful default, not a footgun**: `tessera bundle redact <file>`
   keeps the cited records plus one relation hop (so entity/aggregate
   grammars that walk `sold_to`/resolutions still re-derive) and withholds
   everything else. `--hide-source <glob>` and `--keep-all-cited` refine it.
6. **Governance ties in**: a new fail-closed policy rule group
   `redaction: {allow: false | max_withheld: N}` lets a verifying party
   refuse redacted evidence outright — an auditor who needs the full
   corpus can say so once, in the same policy file as every other control.
7. **Both implementations.** The rule is ported to the independent
   JavaScript verifier in the same unit, and the conformance kit is
   regenerated — a format change that only one implementation understands
   would undo spec 0148.

## Scope

**In:** `bundle/redact.py`, the `format.py` leaf rule + minor 1.2,
`verify.py` redaction-aware claim handling and reporting, the `redaction`
policy rules, `tessera bundle redact`, the JS verifier port, a committed
demo artifact, `tests/test_bundle_redaction.py`, `docs/REDACTION.md`,
README + mkdocs pointers, kit regeneration.
**Out:** redacting `result` (named limit), zero-knowledge proofs of
withheld content (out of scope by ROADMAP3), re-identification defences
for the ids that remain visible.

## Acceptance criteria

- [ ] A redacted bundle's recomputed root equals the original's, and a
      detached approval made over the original **still validates**.
- [ ] **The safety pin:** redacting the falsifying evidence of the forged
      challenge bundle does not produce PASS.
- [ ] A claim citing withheld evidence is reported "not re-derivable
      (withheld)" and the verdict is degraded, never PASS, never FAIL.
- [ ] Claims citing only visible evidence still fully re-derive.
- [ ] The default keeps enough for the business grammars to re-derive on
      the committed bundle; the size drop is measured and documented.
- [ ] `redaction: {allow: false}` refuses a redacted bundle, fail-closed.
- [ ] The JS verifier agrees on every redaction case; kit regenerated with
      zero disagreements.
- [ ] Gate green; six eval lines byte-identical; frozen core empty-diff.

## Eval impact

None — additive.

## Risks / notes

- **The dangerous failure would be silent**: a redacted bundle that still
  says PASS. Decision 3 makes that structurally impossible, and the forged
  + redacted test pins it.
- An attacker can mark anything redacted and put an arbitrary commitment
  there, but this buys nothing: withheld content is unverifiable, so no
  claim gains a verdict — and if the bundle was signed or approved, a
  wrong commitment moves the root and breaks both. Documented explicitly:
  **a redacted bundle proves less, never more.**
