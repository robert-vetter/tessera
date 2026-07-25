# 0151. The issuance ledger — answering "is this all of them?"

- **Phase / milestone:** ROADMAP3 Milestone 22. Trust-bearing and
  adversarially reviewed: it introduces a *completeness* claim, which is a
  new kind of claim for this project.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

Ten layers now answer one question extremely well: **"is this receipt
honest?"** Re-execution, chains, policies, approvals, audit records, a
measured benchmark, a bounded proof, a second implementation, redaction,
and a browser you can drop a file on.

Every one of them is about a receipt you were *given*. None of them
answers the question an auditor asks second, and a regulator asks first:

> **"Is this all of them?"**

An operator can simply not show you a decision. Nothing in the stack makes
a withheld decision detectable — the guarantees are per-artifact, and a
per-artifact guarantee is silent about the set. That is a genuine hole,
and it is the hole every serious transparency system exists to fill.

## Decisions

1. **An append-only Merkle log of issued receipts**
   (`tessera/ledger/`), following the Certificate-Transparency
   construction (RFC 6962): leaves are bundle roots, the head is
   `(size, root)`, and the log supports the two proofs that make it
   meaningful:
   - **inclusion** — a compact path proving *this receipt is in the log
     at that head*;
   - **consistency** — a proof that head *B* extends head *A* without
     rewriting anything, so an operator cannot retroactively delete or
     alter a decision once anyone has seen an earlier head.
   Domain-separated hashing (`0x00` leaf / `0x01` node prefixes) as in RFC
   6962, so a leaf can never be presented as an interior node.
2. **The ledger is separate from the bundle.** No bundle bytes change and
   no root moves: attestation produces a *detached* inclusion-proof
   artifact, exactly like approvals (ADR 0035) and unlike the reserved
   `anchor` section, which stays reserved for the public-log unit (0138).
   A receipt therefore gains a completeness claim without invalidating any
   signature, approval or committed root.
3. **Verification stays offline and honest.** `tessera verify --inclusion
   proof.json --head <size:root>` checks the proof against a head the
   verifier supplies — never one the file supplies, which would be
   self-attestation. Without a head there is nothing to check, and the
   report says so rather than implying it checked.
4. **The honest limit is stated everywhere the feature is: the split
   view.** An operator who keeps *two* logs can show each party a
   different head, and no offline check can detect that. Consistency
   proofs make rewriting detectable **to anyone who has seen an earlier
   head**; making heads unforgeably public is precisely what a
   transparency log (Rekor, unit 0138 — reserved, maintainer-present) is
   for. The docs say this in the same breath as the guarantee, never as a
   footnote.
5. **Governance ties in:** the fail-closed policy engine gains
   `ledger: {require_inclusion: true, head: "<size:root>"}` so a verifying
   party can demand a completeness proof in the same file as every other
   control.
6. **Both implementations.** Inclusion-proof verification is ~30 lines and
   goes into the shared JS core in the same unit, so the browser page can
   check it too — a format/protocol addition only one implementation
   understands would undo ADR 0038/0040.

## Scope

**In:** `tessera/ledger/{tree,store}.py`, `tessera bundle attest`,
`tessera ledger` (head/prove/consistency), `verify --inclusion/--head`,
the `ledger` policy rules, the JS inclusion check, a committed demo log,
`tests/test_ledger.py`, `docs/LEDGER.md`, README + mkdocs pointers.
**Out:** the public transparency log (0138, reserved and irreversible);
gossip protocols; anything that would change bundle bytes or the
`anchor` section.

## Acceptance criteria

- [ ] Inclusion proofs verify for every entry of a log of size 1…N, and
      fail for a root that was never appended.
- [ ] Consistency proofs verify between every pair of sizes, and **fail
      when history is rewritten** — the adversarial pin: an operator who
      alters or drops an earlier entry cannot produce a consistent head.
- [ ] Omission is detectable: a receipt absent from the log has no
      inclusion proof at that head, and the policy rule refuses it.
- [ ] `verify --inclusion` without `--head` reports "not checked" rather
      than passing.
- [ ] Hashing is domain-separated; a leaf cannot be replayed as a node
      (pinned).
- [ ] The JS core verifies the same proofs; kit regenerates unchanged.
- [ ] Gate green; six eval lines byte-identical; no bundle byte changes.

## Eval impact

None — additive.

## Risks / notes

- **Overclaim risk is real and specific**: a ledger proves *inclusion in a
  log*, not *completeness of the world*. The claim must always be phrased
  against a head the verifier already trusts. Decision 4 is the mitigation
  and it is repeated in the CLI output, the docs and the policy detail
  text.
- Implementing Merkle proofs by hand is a correctness risk; mitigated by
  exhaustive small-size tests (every entry of every size up to N, every
  consistency pair) rather than spot checks.
