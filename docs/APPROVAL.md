# Verifiable approvals — the sign-off as a cryptographic artifact

*Milestone 22 (spec 0145, ADR 0035). The second half of the positioning
line — "only do what you approve" — becomes cryptographic.*

An approval answers the two questions every enterprise sign-off dispute
is made of: **who** approved, and **what exactly** did they approve. It
is a detached JSON artifact: an Ed25519 signature over a payload
containing the bundle's sealed root — so "what" means *these exact
bytes*, not "roughly that decision".

```console
$ uv run tessera bundle keygen --key mgr1.key
$ uv run tessera bundle approve decision.tsb --key mgr1.key --note "quarterly review"
approved: root sha256:5cc23099dccc…
by key:   df5c927a701e…
wrote:    decision.tsb.approval.json

$ uv run tessera verify decision.tsb --approval decision.tsb.approval.json
…
approvals: 1/1 valid — each binds a key to this exact sealed root
  [ok] approved by key df5c927a701e… (quarterly review)
```

**Change one digit of the decision and re-seal: the root moves, and
every prior approval reads INVALID with the mismatch named.** The
committed challenge pair demonstrates it — the forged bundle cannot
borrow the honest bundle's approval:

```console
$ uv run tessera verify data/challenge/forged.tsb --approval honest.approval.json
approvals: 0/1 valid — each binds a key to this exact sealed root
  [!!] approved by key df5c… — approves a different bundle: the artifact
       approves root sha256:5cc23099dccc…, this bundle's recomputed root
       is sha256:9ebb66f3ae04… — an approval binds to exact bytes
```

## Four-eyes in one policy line

Approvals **inform**; [trust policies](POLICY.md) **enforce**. The
`approvals` rule group counts only *valid* approvals (and only allowed
ones when a key list is given):

```json
{
  "name": "four-eyes",
  "version": 1,
  "rules": {
    "require_rederived": true,
    "approvals": {
      "require": 2,
      "distinct_approvers": true,
      "allowed_approvers": ["<mgr1 hex key>", "<mgr2 hex key>"]
    }
  }
}
```

`tessera verify decision.tsb --approval a1.json --approval a2.json
--policy four-eyes.json` → COMPLIANT (exit 0) with both approvals;
remove one and it exits 5 with the count named. The same fail-closed
engine as every policy rule: verify run *without* approval files against
this policy is a violation ("0 valid approvals"), never a vacuous pass —
and a duplicate key counts once when `distinct_approvers` is set (the
same pair of eyes twice is not four eyes).

## Honest limits

- **An approval binds a key, not a person.** Key distribution and role
  mapping are out of scope (ADR 0032), exactly as for bundle signing —
  compare keys against a list you trust (that is what
  `allowed_approvers` is for).
- **Identity, not time.** The optional `--at` field is the approver's
  *signed claim*, not proof — proving *when* honestly requires a
  transparency log (the reserved anchor unit). No timestamp theater.
- **Approvals never change the bundle's own verdict.** They are
  attestations *over* it; a FAIL bundle with ten valid approvals is
  still a FAIL (exit precedence 4 > 2 > 5 > 3 > 0 — approved lies are
  still lies).
- Creating an approval needs the `sign` extra (PyNaCl); **checking one
  is pure stdlib** — `tessera verify` stays dependency-free on a clean
  clone.
- Revocation is named future work (a detached revocation artifact would
  mirror this design); until then, approval sets are additive.
