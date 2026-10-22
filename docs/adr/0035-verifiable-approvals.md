# 0035. Approvals as detached signed artifacts bound to the sealed root

- **Status:** accepted (2026-07-18, spec 0145)
- **Context:** ROADMAP3 Milestone 22 — making the second half of the
  positioning line ("only do what you approve") cryptographic: an
  approval must prove *who* approved *what*, where "what" is the exact
  sealed state, not a description of it.

## Context

Action receipts record `requires_approval` and `approved` as flags —
sufficient for the drafted-never-sent gate, insufficient as evidence:
nothing binds an approver's identity to the exact decision bytes. In
enterprise approval workflows the disputes are precisely "that is not
what I approved" and "who approved this" — both answerable only if the
approval is a verifiable artifact over the exact content.

## Decision

An approval is a **detached JSON artifact**: an Ed25519 signature over
the canonical bytes of a payload containing the bundle's sealed
`integrity.root` (plus an optional note and an optional, *claimed*
date). Creation needs the `sign` extra (the spec-0135 pattern);
**checking is pure stdlib** via the existing RFC 8032 verifier, so
`tessera verify --approval a.json` adds no dependency.

1. **Detached, never a bundle section.** The section set is closed and
   byte-stable (ADR 0031); an approval is a third party's post-seal act.
   Embedding it would re-seal the bundle — changing the very root that
   was approved — and cap the approver count at the format's shape.
   Detached artifacts compose: N approvers, any time, bundle untouched.
   This is the same layering as trust policies (ADR 0034): the bundle
   carries evidence; surrounding artifacts carry judgment.
2. **Bound to the root, checked against the recomputed root.** The
   verifier compares `approves_root` to the root it recomputes from the
   file's content — so an approval detaches from any tampered-and-
   re-sealed descendant automatically: change one digit, the root
   moves, every prior approval reads INVALID with the mismatch named.
3. **Identity, not time.** The artifact proves who (a key) approved
   what (a root). The optional `at` field is the approver's signed
   *claim*; proving time honestly requires a transparency log — the
   reserved anchor/Rekor unit. Stated plainly in the docs; no timestamp
   theater.
4. **Approvals inform; policies enforce.** Approval checks appear in
   the verify report (valid/invalid, named) and never alter the
   bundle's own verdict — they are attestations *over* it. Enforcement
   is a policy concern: the fail-closed `approvals` rule group
   (`require`, `allowed_approvers`, `distinct_approvers`) counts only
   valid (and, when listed, allowed) approvals; a verify run without
   approval files against such a policy is a violation, not a vacuous
   pass.

## Alternatives rejected

- **An `approvals` bundle section:** re-seals the approved content
  (self-defeating), caps composition, breaks byte-stability of
  committed artifacts. Rejected on the same grounds as embedded
  policies.
- **Approval = a second signature in the existing `signature` slot:**
  conflates origin ("who sealed this") with judgment ("who approved
  this"), and the slot is single by format.
- **A trusted timestamp in the artifact:** unverifiable self-claim
  dressed as proof; deferred to the transparency-log unit where it can
  be honest.
- **Counting recorded `approved=true` flags as approval evidence:** the
  flag is the *gate's* state, writable by the emitter; evidence of
  approval must be producible only by the approver's key.

## Consequences

- Four-eyes becomes one policy line, enforced by the same fail-closed
  engine as every other control, and auditable offline forever.
- An approval binds a key, not a person — key distribution and role
  mapping stay out of scope (ADR 0032), stated wherever approvals are
  documented.
- Revocation is named future work (a detached revocation artifact could
  mirror this design); until then, approval sets are additive.
- The audit record (0139) can later cite approvals alongside the policy
  hash — "decision X, verified under policy Y, approved by keys A,B" —
  natural composition, not built here.
