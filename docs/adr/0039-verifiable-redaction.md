# 0039. Redaction by commitment: the root survives, the verdict never improves

- **Status:** accepted (2026-07-18, spec 0149)
- **Context:** ROADMAP3 Milestone 22 — the quietest adoption blocker in the
  whole stack: a trust bundle carries the evidence, so the receipt cannot
  leave the building.

## Context

Everything built in Milestones 20–22 assumes the artifact can be handed
over. In practice it usually cannot: the evidence closure contains
customer master data, log lines and ticket text, and sharing a decision
would mean sharing the corpus it was decided on. The strongest artifact
this project produces therefore stays internal — which is a product
problem disguised as a privacy problem.

Verifiable credentials solved the analogous problem with selective
disclosure. The question this ADR settles is *how* to withhold evidence
without either (a) breaking verification or (b) letting redaction become
a laundering tool.

## Decision

**Withhold content, keep the commitment, preserve the root.**

1. **A withheld item contributes the leaf digest the bundle was sealed
   with.** A redacted graph node becomes `{"redacted": true, "record":
   {"id": …}}`; a withheld section becomes `{"redacted": true}`. Manifest
   recomputation substitutes the stored commitment for those leaves, so
   the manifest and root recompute **bit-for-bit identically**. The
   practical payoff: a signature or a detached approval made over the
   original still verifies over the redacted copy — the auditor checks the
   same root the approver signed.
2. **The record id stays; nothing else does.** Citations and referential
   integrity must still resolve. Ids are therefore visible by design, and
   the documentation says so rather than implying anonymity.
3. **A redacted bundle can never report PASS.** A claim citing withheld
   evidence is reported *not re-derivable here* — not as a mismatch, which
   would read as a lie when the truth is "not shared" — and any redaction
   forces the degraded path. Answer re-derivation is not attempted at all
   on a deliberately partial corpus, because re-running the router would
   produce a different answer and read as a forgery.
4. **Safety over convenience:** *redaction can hide, but it can never
   upgrade a verdict.* An attacker who withholds exactly the evidence that
   exposes a forgery gets DEGRADED, with every affected claim visibly
   un-re-derived — never PASS. This is the pinned test the unit rests on.
5. **Governance, not just capability:** the fail-closed policy engine
   gains `redaction: {allow, max_withheld}`, so a verifying party that
   needs the complete corpus says so once, in the same file as every other
   control.
6. **Both implementations, same unit.** The rule is ported to the
   independent JavaScript verifier immediately; a format change only one
   implementation understands would undo ADR 0038.

## Why taking the stored commitment is safe

It looks circular — the manifest vouching for content that is absent — so
the argument is worth stating plainly. An attacker can mark anything
withheld and place any commitment there, but this buys nothing:

- withheld content is **unverifiable**, so no claim can be re-derived from
  it and no verdict can improve;
- if the bundle was signed or approved, a wrong commitment moves the root
  and breaks both attestations;
- what remains is an artifact that proves *less*.

**A redacted bundle proves less, never more** — which is exactly the
property a disclosure mechanism should have.

## Alternatives rejected

- **Re-seal after removing content.** Simple, and it destroys the point:
  the root moves, so every prior signature and approval is invalidated and
  the redacted copy can no longer be tied to the decision that was signed.
- **Bump the format minor for redacted bundles** (spec 0149's own first
  draft). `format` is itself a manifest leaf, so touching it moves the
  root. The per-file feature-level trick works for chains — which are *new*
  bundles — but not for a transformation of an already-sealed one.
  Redaction is self-describing through its markers instead. Recorded as a
  correction rather than quietly dropped.
- **Redacting `result` too.** The claims are the finding being shared;
  removing them leaves nothing to verify. The honest limit is stated
  instead: evidence a claim *cites* remains visible in the claim's own
  support, and what redaction removes is the far larger uncited corpus.
- **Zero-knowledge proofs over withheld content.** Out of scope by
  ROADMAP3 and unnecessary for the use case: the auditor needs to know
  *what was withheld and what that costs*, not to verify hidden data.

## Consequences

- A decision can be shared with an auditor, a customer or a regulator
  while the corpus stays home, and the receipt still carries a checkable
  root, signature and approval.
- Redacted bundles are visibly weaker, by construction — the verdict says
  so, in both implementations.
- The committed demo (`data/redacted/honest-public.tsb`) shows the effect
  concretely: same root as the public challenge bundle, 404 KB → 164 KB,
  all three claims still re-deriving.
