# 0034. Trust policies: the auditor's rules, re-executed at verify time

- **Status:** accepted (2026-07-18, spec 0144)
- **Context:** ROADMAP3 Milestone 22 — giving platform/governance teams
  a way to state their controls once and prove, offline and after the
  fact, that an agent decision was checked against them.

## Context

Enterprise governance is expressed as controls: four-eyes approval,
segregation of duties, allowed systems of record, signed origin. Trust
bundles carry everything needed to *check* such controls — verdicts,
signatures, cited sources, action receipts, embedded upstream chains —
but until now the check itself lived in a human's head. The question
this ADR fixes is *where the rules live and when they run*.

## Decision

A **trust policy** is a small, versioned JSON document owned by the
verifying party, applied at verification time:

    tessera verify decision.tsb --policy policies/signed-chain.json

1. **Policy-at-verify, never policy-in-bundle.** A bundle that
   self-attests compliance is a rubber stamp — the exact failure mode of
   the integrity-only receipt systems this project answers. The policy
   is the auditor's document; the evidence was sealed without knowing
   which policy it would face, and the rules re-execute against the
   sealed content. This also means **zero format change**: every
   existing bundle, including the committed challenge pair and the chain
   brief, is immediately policy-checkable.
2. **Fail-closed rule parsing.** An unknown rule key, a malformed value,
   or an unreadable policy file refuses evaluation with a named error.
   A typo in a guardrail must surface as a refusal, never as a silent
   pass. This is also what makes the vocabulary safely extensible: a
   newer policy meeting an older verifier refuses loudly.
3. **Deterministic rule vocabulary over existing evidence.** v1 rules
   read only what the bundle and the verify report already prove:
   signature status/keys, re-derivation taxonomy, per-claim verdicts,
   cited evidence sources (glob allowlist), action gate flags
   (`requires_approval`, `sent`, `simulated`), and chain structure
   (depth; per-upstream signature status/keys from the recursive
   verification). No rule introduces new evidence semantics.
4. **Exit code 5, precedence `4 > 2 > 5 > 3 > 0`.** A broken or lying
   bundle keeps its stronger verdict (policy can never upgrade it); a
   sound bundle that violates the rules — or an unusable policy — exits
   5 with each violation named; a compliant degraded bundle remains 3.
5. **Scoped verdict language, pinned.** COMPLIANT means: this policy
   (by name and canonical sha256), these rules, this file. It is not
   correctness, not legal compliance, not certification; the rendered
   output states this verbatim and a test asserts it.

## Alternatives rejected

- **Policy embedded in the bundle** (self-attested compliance): rubber
  stamp; also forces a format bump and re-sealing to change a rule.
- **Policy checks at emission only:** the emitter is the party under
  audit; controls checked by the controlled are not controls. Emission
  MAY be policy-aware later (a convenience), but the load-bearing check
  is the verifier's.
- **A general policy language** (CEL/OPA-style): expressive power buys
  audit opacity — a Turing-ish guardrail cannot be reasoned about by
  reading it. A closed, named rule vocabulary keeps every policy
  human-legible and every verdict explainable in one line.
- **Ignore-unknown-rules parsing** (the usual forward-compat default):
  silently skipping a misspelled or newer rule inverts the safety
  property of a guardrail. Fail-closed is the point.

## Consequences

- Governance teams can version policies in their own repos; the policy
  hash in the output ties any recorded verdict to the exact rule text.
- The vocabulary grows by ADR-recorded additions; fail-closed semantics
  make growth non-breaking in the dangerous direction.
- `UpstreamCheck` carries signature status/signer (additive fields), so
  chain signer rules read the recursion the verifier already performs.
- Cross-referencing policies from audit records (0139) is natural
  future work: "decision X verified under policy Y (sha256 …)".
