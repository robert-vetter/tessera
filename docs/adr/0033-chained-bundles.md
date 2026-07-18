# 0033. Chained bundles: a hash-DAG of embedded upstreams, re-executed recursively

- **Status:** accepted (2026-07-18, spec 0143)
- **Context:** ROADMAP3 Milestone 22 — extending the trust bundle from a
  single decision to a pipeline of decisions without weakening either of
  the act's two load-bearing properties: verification is **offline from
  the file alone**, and verification means **re-execution**, never trust
  in recorded verdicts.

## Context

Agent systems in production are pipelines: one agent's output becomes
the next agent's input. A trust bundle attests one decision. What passes
between agents is unverified text, so the pipeline's audit trail breaks
exactly at the hand-offs — the same integrity-only gap Act 3 exists to
close, one level up. The question this ADR fixes is *how a bundle may
cite another bundle* such that one `tessera verify` still proves the
whole chain from one file, offline.

## Decision

A chain bundle is an ordinary trust bundle whose evidence corpus is
derived from other bundles' verifier-passing claims, with three format
commitments (format minor 1.1, additive per ADR 0031's rule — a new key
is a minor bump. The minor is a **per-file feature level**: a chain
bundle declares 1.1; a single-decision bundle uses no 1.1 feature and
keeps declaring 1.0, so the committed challenge artifacts — whose roots
are public identity — stay byte-stable. Verification never gates on
minor):

1. **Embed, don't reference.** The closure kind `chain-snapshot` carries
   the full sealed upstream bundles in `evidence_closure.upstream`,
   alongside the derived `graph`/`kb` the chain answer was computed
   against. The bundle stays self-contained: a stranger needs the one
   file and the standard library, nothing else.
2. **The manifest commits to the upstream set by root.** One integrity
   leaf per upstream, named `upstream:<root>`, hashing the embedded
   bundle's canonical bytes; duplicate roots rejected. The chain is
   thereby a depth-1 hash-DAG: the chain root commits to each upstream's
   root *and* bytes. Cycles are impossible by construction — embedding
   requires the upstream's final sealed bytes, so no bundle can contain
   its own root.
3. **Re-execution recurses; recorded verdicts are never trusted.**
   `tessera verify` on a chain bundle (a) re-verifies every embedded
   upstream with the full verifier — envelope, signature if present,
   structural checks, claim re-derivation, answer re-derivation — and
   requires PASS, propagating any failure with the upstream root named;
   (b) requires every derived kb record to byte-match the cited upstream
   claim at its recorded index, and that claim to have **re-derived** in
   the upstream's own re-execution; (c) re-runs the deterministic chain
   route (the frozen core's lexical retrieval, called not modified) over
   the packaged corpus and requires canonical-byte equality with the
   recorded result. "You can only cite what re-verifies" holds at
   emission (a non-PASS upstream refuses to chain) and is re-checked at
   verification (the emitter is never trusted either).

The chain domain is **bundle-native**: the dispatch lives in the bundle
layer, and the `GroundedDomain` registry, the agent chain, and the frozen
core stay byte-identical.

## Alternatives rejected

- **Flat merge** (ingest upstream corpora into one closure, no
  boundaries): loses per-link attribution and the ability to name which
  upstream failed; a tamper anywhere degrades the whole corpus
  anonymously. The boundary *is* the audit value.
- **Reference by root without embedding** (fetch upstreams at verify
  time): breaks "from the file alone" — the one property every design
  decision in Act 3 defends. Size is the price and it is measured.
- **Trusting upstream recorded verdicts** (skip recursive re-execution):
  a rubber stamp — the exact failure mode of the integrity-only receipt
  systems this project exists to answer. Rejected on thesis.
- **Registering a chain domain in `agent/grounded.py`**: works, but
  edits the agent chain that Milestones 20–21 audited byte-identical,
  for zero user-visible gain over bundle-layer dispatch.

## Consequences

- A chain bundle's size is the sum of its embedded upstreams plus the
  derived corpus (the committed demo records the real numbers).
- Verification cost is linear in the number of links; depth in practice
  is small, recursion is structural and backstopped (no input crashes
  verify).
- A verifier older than format minor 1.1 refuses the unknown closure
  kind toward degradation, never toward a false PASS (the kind label is
  advisory; re-execution is gated on content, per the spec-0134 fix).
- The Auditability Floor's mutation battery does not yet include
  cross-bundle classes; the attack classes are pinned in this unit's
  tests and the floor extension is named future work (spec 0143 D9).
