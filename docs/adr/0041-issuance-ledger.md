# 0041. An issuance ledger — the completeness axis, bounded honestly

- **Status:** accepted (2026-07-18, spec 0151)
- **Context:** ROADMAP3 Milestone 22 — ten layers answer "is this receipt
  honest?"; none answers "is this all of them?"

## Context

Every guarantee shipped so far is *per artifact*: re-execution, chains,
policies, approvals, audit records, redaction, and two implementations
that agree. All of them concern a receipt you were **given**. An operator
who simply does not show you a decision defeats the entire stack, and no
per-artifact property can notice.

That is the completeness axis, and transparency logs exist precisely for
it.

## Decision

An **append-only Merkle log of issued receipt roots**, built as
Certificate Transparency builds one (RFC 6962), with the two proofs that
make a log meaningful: **inclusion** (this receipt is in the log at that
head) and **consistency** (this head extends that earlier head with
nothing rewritten).

1. **Detached, never in the bundle.** Attestation emits a separate
   inclusion-proof artifact, like an approval (ADR 0035). No bundle byte
   changes and no root moves, so signatures, approvals and every committed
   artifact stay valid. The reserved `anchor` section stays reserved for
   the public-log unit.
2. **The head comes from the verifier, never from the file.** A proof that
   vouches for its own head is self-attestation — the failure mode this
   whole project answers. `verify --inclusion` requires `--head`, and
   without one it reports *not checked* rather than passing.
3. **Domain-separated hashing** (`0x00` leaves / `0x01` nodes) so a leaf
   can never be presented as an interior node.
4. **Correctness established exhaustively, not by sampling**: every entry
   of every log size and every consistency pair up to 40 are verified in
   the test suite, plus adversarial cases (rewrite, deletion, truncated
   and padded proofs, unrecorded receipts).
5. **Fail-closed governance**: `ledger: {require_inclusion: true}` in a
   policy demands a completeness proof; not supplying one is a violation,
   not a pass.
6. **Both implementations.** Inclusion verification is in the shared JS
   core, so the CLI, the kit and the browser page all understand it — a
   protocol addition only one implementation understands would undo
   ADR 0038/0040.

## The bound, stated with the guarantee

A local log proves **inclusion relative to a head you already hold** and
**that history was not rewritten** for anyone who has seen an earlier
head. It does **not** prove completeness of the world: an operator who
keeps *two* logs can show two parties two heads, and no offline check
detects that split view. Closing it requires heads to be unforgeably
public — which is exactly what a public transparency log does, and is the
reserved, maintainer-present unit. The docs, the CLI help and the policy
detail text all say this; it is never a footnote.

## Alternatives rejected

- **Putting the proof inside the bundle.** It would move the root and
  invalidate every prior signature and approval, and a self-carried head
  proves nothing.
- **A blockchain.** The property needed is append-only with cheap
  membership proofs; CT's construction supplies it in ~150 lines with no
  network, no consensus and no token.
- **Trusting a signed "count of decisions".** A signed number is a claim,
  not a proof; inclusion and consistency are checkable.
- **Waiting for the public log (unit 0138).** That unit is irreversible
  and identity-bearing, so it stays maintainer-present. The local ledger
  is the honest, offline part of the same idea and is useful on its own.

## Consequences

- The stack gains an axis it did not have, with the strongest available
  offline guarantee and an explicitly named remaining gap.
- Publishing a head periodically (in a report, an email, a commit) is now
  a meaningful act: every earlier head anyone holds constrains the
  operator forever after.
- The public transparency log becomes an *upgrade path* rather than a
  prerequisite.
