# 0144. Trust policies — governance-as-code, re-executed by the verifier

- **Phase / milestone:** ROADMAP3 Milestone 22 (the public proof) — an
  added unit in the 0142/0143 pattern. Trust-bearing (it renders
  compliance-flavored verdicts) → honesty rules pinned in tests.
- **Issue:** —
- **Status:** approved (autonomous session; decision and rationale
  recorded here per CLAUDE.md "Autonomous phase execution").

## Problem

Enterprise platform teams govern software with **controls** — four-eyes
approval, segregation of duties, system-of-record allowlists, signed
origin — not with vibes. Today those controls stop at the copilot
boundary: a Joule-style assistant answers, acts, and hands off, and the
platform team has no way to state its rules once and prove, later and
offline, that every agent decision was checked against them. Tessera
has the receipts (bundles), the pipelines (chains), and the regulator
language (audit records); what is missing is the **guardrail file**.

This unit adds it: a *trust policy* is a small, versioned JSON document
of deterministic rules; `tessera verify <file> --policy <policy.json>`
re-executes the rules against the sealed evidence — every rule PASS or
VIOLATED with a named cause, over chains recursively where the rule says
so — offline, from the two files alone.

**Why the policy lives with the verifier, not inside the bundle (the
core design decision, ADR 0034):** a bundle that self-attests "I am
compliant" is a rubber stamp — exactly the failure mode this project
exists to answer. The policy is the *auditor's* document, applied at
verification time to evidence that was sealed without knowing which
policy it would face. Same primitive as everything in Act 3:
re-execution, not recorded assertion. Zero format change; every
existing bundle (including both challenge bundles and the chain brief)
is immediately policy-checkable.

**Why this unit now (the audience test, recorded):** the maintainer
asked for the feature an SAP/Joule-shaped enterprise buyer would rate
highest. Candidates: HANA bundle storage (plumbing, tier-gated),
delegation key hierarchies (heavy crypto surface; ADR 0032 deliberately
scoped key distribution out), CI action (packaging), policies. Policies
win: they speak the buyer's native vocabulary (controls), they compose
with every shipped artifact, and they are deterministic, offline,
additive, and demonstrable in one command.

## Decisions

1. **Policy = versioned JSON, fail-closed.** `{"name", "version",
   "rules": {...}}`. An unknown rule key, a malformed value, or an
   unreadable file **refuses evaluation** (a typo must never silently
   pass as compliant). The policy's canonical sha256 is printed and
   carried in the JSON output, so an audit record can cite exactly which
   policy text was applied.
2. **Rule vocabulary v1** — every rule provable from the bundle + the
   verify report, no new evidence semantics:
   - `require_signed` (bool) · `allowed_signers` (list of hex keys)
   - `require_rederived` (bool): taxonomy must be RE-DERIVED
   - `forbid_unverified_claims` (bool): every recorded claim re-derived
     and matching (refusals satisfy trivially)
   - `allowed_evidence_sources` (list of globs): every cited support
     source must match one pattern (system-of-record allowlist)
   - `actions.allow` (bool): false → a read-only agent, no action section
   - `actions.require_approval_gate` (bool): a packaged action must
     record `requires_approval=true`
   - `actions.forbid_real_send` (bool): `sent=false`, `simulated=true`
   - `chain.max_depth` (int): embedded-upstream nesting bound (walked on
     the bundle, recursively)
   - `chain.require_signed_upstreams` (bool) ·
     `chain.allowed_upstream_signers` (list of hex keys)
3. **Evaluation = pure function** `evaluate_policy(policy, bundle,
   report) -> PolicyReport` in `tessera/bundle/policy.py` — stdlib-only,
   offline, deterministic; each rule yields PASS/VIOLATED with a named
   detail; `compliant` iff all rules pass. The verify CLI grows
   `--policy <path>`; text output appends a policy section; `--json`
   with `--policy` emits `{"verify": ..., "policy": ...}`.
4. **Exit code 5 = the policy layer**, slotting into the precedence
   `4 > 2 > 5 > 3 > 0`: envelope/semantic failures of the bundle keep
   their meaning (a broken bundle is worse than a non-compliant one);
   a sound bundle that violates policy — or an unusable policy file —
   exits 5, named; a compliant degraded bundle stays 3.
5. **Chain support:** `UpstreamCheck` gains `signature_status` /
   `signer` (additive, defaulted), filled from each upstream's recursive
   report, so chain signer rules read the same recursion the verifier
   already runs. `chain.max_depth` walks the embedded structure.
6. **Committed example policies** under `policies/` (three: a read-only
   agent, a four-eyes drafted-action gate, a signed-chain rule set) —
   used verbatim by docs and tests.
7. **Docs:** `docs/POLICY.md` (the guardrail file, the rule table, the
   two-command demo incl. a deliberate NON-COMPLIANT run on the chain
   brief, honest limits); README pointer; mkdocs nav; one paragraph in
   `SAP_ALIGNMENT.md` mapping the rule vocabulary to the enterprise
   controls it mirrors (four-eyes, SoD-flavored read-only, system-of-
   record allowlists) — mapping language only, no integration claim.

## The honesty guardrails

- **"COMPLIANT" means: these rules, this policy hash, this file —
  nothing more.** Not correctness, not legal compliance, not
  certification. The rendered output says so verbatim (pinned).
- Policy checks **consume** the verifier's re-execution; they never
  soften it (a policy cannot upgrade a FAIL/TAMPERED bundle — exit
  precedence pins this).
- Fail-closed on unknown rules (pinned): misspelling `require_signed`
  is a refusal to evaluate, never a silent pass.
- Joule is referenced only as "Joule-style" (existing docs language);
  no SAP integration is claimed anywhere.

## Scope

**In:** `bundle/policy.py`, `UpstreamCheck` signature fields, verify CLI
`--policy`, `policies/{read-only,four-eyes-drafted,signed-chain}.json`,
`tests/test_bundle_policy.py`, `docs/POLICY.md`, SAP_ALIGNMENT
paragraph, README + mkdocs pointers.
**Out:** embedding policies in bundles (rejected, ADR 0034), policy
authorship UI, org key hierarchies (ADR 0032 scope), Rekor (0138),
write-up (0141).

## Acceptance criteria

- [ ] Every rule has a violated-case test with its named detail.
- [ ] Unknown rule key / malformed policy → refusal to evaluate, exit 5,
      named (fail-closed pinned).
- [ ] `verify data/chain/brief.tsb --policy policies/read-only.json` →
      COMPLIANT, exit 0; `--policy policies/signed-chain.json` →
      NON-COMPLIANT (unsigned), exit 5, rule named.
- [ ] An action bundle satisfies `four-eyes-drafted`; a bundle with a
      real-send forgery violates it (named).
- [ ] Exit precedence pinned: FAIL bundle + any policy → 2; TAMPERED →
      4; compliant DEGRADED → 3.
- [ ] `--json --policy` round-trips; policy sha256 present and stable.
- [ ] stdlib-only leak-guard; gate green; six eval lines byte-identical;
      frozen core + agent chain empty-diff.

## Eval impact

None — additive module + CLI flag + docs + tests.

## Risks / notes

- The word "policy" invites overclaim; the disclaimer line and the
  scoped meaning of COMPLIANT are test-pinned like 0139's.
- Rule vocabulary will grow; fail-closed semantics make growth safe
  (old verifiers refuse new rules rather than ignoring them).
