# Trust policies — governance as code, re-executed by the verifier

*Milestone 22 (spec 0144, ADR 0034). Write the guardrail once; every
agent decision can be checked against it — offline, after the fact,
from two files.*

Enterprise platform teams govern software with **controls**: four-eyes
approval, segregation of duties, allowed systems of record, signed
origin. Until now those controls stopped at the copilot boundary. A
*trust policy* is a small, versioned JSON document of deterministic
rules; `tessera verify` re-executes them against the sealed evidence:

```console
$ uv run tessera verify data/chain/brief.tsb --policy policies/read-only.json
…
verdict:   PASS (exit 0)

policy:    read-only-agent v1 (sha256:b5a53ead18ed…) — COMPLIANT
  [ok] require_rederived: the verdicts were re-executed from the packaged evidence
  [ok] forbid_unverified_claims: all 5 recorded claim(s) re-derive and match
  [ok] actions.allow: no action packaged — a read-only decision

$ uv run tessera verify data/chain/brief.tsb --policy policies/signed-chain.json
…
policy:    signed-chain v1 (sha256:36eedd67b7ee…) — NON-COMPLIANT
  [!!] require_signed: the bundle is unsigned (or its signature does not verify)
  [ok] require_rederived: the verdicts were re-executed from the packaged evidence
  [ok] chain.max_depth: embedded chain depth 1 (limit 3)
  [!!] chain.require_signed_upstreams: unsigned upstream(s): […]
$ echo $?
5
```

Three example policies ship in [`policies/`](https://github.com/robert-vetter/tessera/tree/main/policies):
a **read-only agent** (no actions, everything re-derived), a **four-eyes
gate for drafted actions** (`requires_approval` recorded, nothing ever
really sent), and a **signed chain** (signed bundle, signed upstreams,
bounded depth).

## Where the policy lives — and why

**With the verifier, never inside the bundle.** A bundle that
self-attests "I am compliant" is a rubber stamp — the exact failure mode
of integrity-only receipts. The policy is the *auditor's* document,
applied at verification time to evidence that was sealed without knowing
which policy it would face. Re-execution, not recorded assertion — the
same primitive as everything else here. This also means zero format
change: every existing bundle, including the [challenge](CHALLENGE.md)
pair and the [chain brief](CHAIN.md), is immediately policy-checkable.

**Fail-closed.** An unknown rule key, a malformed value, or an
unreadable policy refuses evaluation with a named error (exit 5). A typo
in a guardrail must surface as a refusal, never as a silent pass.

## The rule vocabulary (v1)

Every rule is provable from the bundle and the verifier's own
re-execution — no rule introduces new evidence semantics.

| Rule | Enforces |
|---|---|
| `require_signed` | the bundle carries a valid Ed25519 signature over its root |
| `allowed_signers` | the signer's key is on the list |
| `require_rederived` | the verdicts were re-executed here (taxonomy RE-DERIVED) |
| `forbid_unverified_claims` | every recorded claim re-derives and matches |
| `allowed_evidence_sources` | every cited source matches an allowlist glob (system-of-record) |
| `actions.allow: false` | a read-only decision — no action section |
| `actions.require_approval_gate` | a packaged action records `requires_approval=true` |
| `actions.forbid_real_send` | the action is a simulated draft (`sent=false`) |
| `chain.max_depth` | embedded-upstream nesting is bounded |
| `chain.require_signed_upstreams` | every embedded upstream is signed (checked on the recursion) |
| `chain.allowed_upstream_signers` | every upstream's signer is on the list |
| `approvals.require` | at least N **valid** [approval artifacts](APPROVAL.md) of this exact root |
| `approvals.allowed_approvers` | every valid approval is from a listed key (outsiders never count) |
| `approvals.distinct_approvers` | a duplicate key counts once — four eyes means four eyes |

Exit codes compose with the verifier's, precedence **4 > 2 > 5 > 3 > 0**:
a broken or lying bundle keeps its stronger verdict (a policy can never
upgrade it); a sound bundle that violates policy — or an unusable policy
file — exits **5**, each violation named; a compliant degraded bundle
stays 3. `--json` emits `{"verify": …, "policy": …}`, including the
policy's canonical sha256, so a recorded verdict cites the exact rule
text it was checked under.

## Honest limits

- **COMPLIANT means: this policy, these rules, this file.** Not
  correctness, not legal compliance, not certification — the output
  states this verbatim, and a test pins the sentence.
- The vocabulary is deliberately closed (no general policy language):
  expressive power buys audit opacity; a guardrail should be legible by
  reading it (ADR 0034 records the rejected alternatives).
- The four-eyes rule checks the recorded **gate** on drafted actions —
  by design nothing in a bundle was ever really sent, so "approved and
  executed" is the execution layer's record, not the bundle's.
- Policy checks consume the verifier's re-execution; on a degraded
  bundle whose chain was not re-executed, upstream rules fail closed
  ("could not be checked") rather than passing vacuously.
