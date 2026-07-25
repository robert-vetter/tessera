# Verifiable redaction — send the receipt, keep the data

*Milestone 22 (spec 0149, ADR 0039). The quietest adoption blocker in the
whole stack, removed: a trust bundle can now leave the building without
its evidence.*

Every layer before this one assumed the receipt could be handed over. In
practice it usually cannot — the evidence closure carries customer master
data, log lines and ticket text, so sharing a decision meant sharing the
corpus it was decided on. Redaction withholds that content **without
moving the root**:

```console
$ uv run tessera bundle redact data/challenge/honest.tsb
withheld: 337 item(s)
root:     sha256:5cc23099dccc… (UNCHANGED — approvals still verify)
size:     404,339 -> 164,431 bytes
verdict:  DEGRADED — a redacted bundle proves less, never more
```

The root is byte-identical to the original's, so **a signature or a
detached [approval](APPROVAL.md) made before redaction still verifies
afterwards** — the auditor checks the same root the approver signed. A
committed demo ships at `data/redacted/honest-public.tsb`: the public
[challenge](CHALLENGE.md) bundle with its uncited corpus withheld, same
root, all three claims still re-deriving.

## How it works

A withheld item keeps the **commitment** it was sealed with instead of its
content: a redacted graph node becomes `{"redacted": true, "record":
{"id": …}}`, a withheld section becomes `{"redacted": true}`, and manifest
recomputation substitutes the stored leaf digest for exactly those
entries. Everything else is recomputed from content as always, so
tampering anywhere else still breaks the envelope.

The **record id stays** — citations and referential integrity must
resolve — and nothing else does: no text, no origin, no attributes. Ids
are visible by design; this is disclosure control, not anonymity.

By default `redact` keeps the cited records plus **one relation hop**,
which is what the entity and aggregate grammars walk (`sold_to`,
resolutions, mentions). That is why the demo's claims still re-derive
while 337 items stay home.

## The safety property

> **Redaction can hide, but it can never upgrade a verdict.**

- A claim citing withheld evidence is reported *not re-derivable here* —
  not as a mismatch, which would read as a lie when the truth is "not
  shared".
- Any redaction forces the degraded path. **A redacted bundle can never
  report PASS**, even when every visible claim re-derives perfectly.
- Answer re-derivation is not attempted on a deliberately partial corpus:
  re-running the router would yield a different answer and read as a
  forgery, so the verifier states it was not performed.

Take the forged challenge bundle and withhold exactly the evidence that
exposes it — the strongest laundering attempt available:

```console
$ uv run tessera verify hidden.tsb
integrity: intact — every leaf and the root re-computed
withheld:  341 item(s)
claims:    0/3 re-derived
verdict:   DEGRADED (exit 3)
```

Not PASS. Every affected claim is visibly un-re-derived. That case is a
pinned test.

**Why taking the stored commitment is safe** (it looks circular, so the
argument is worth stating): an attacker can mark anything withheld and put
any commitment there, but withheld content is *unverifiable* — no claim
can be re-derived from it, so no verdict improves; and if the bundle was
signed or approved, a wrong commitment moves the root and breaks both. A
redacted bundle proves **less**, never more.

## Governance

Disclosure is a control like any other, so it lives in the same
[policy](POLICY.md) file:

| rule | enforces |
|---|---|
| `redaction.allow: false` | this verifier requires the complete evidence |
| `redaction.max_withheld: N` | at most N items may be withheld |

Fail-closed like every policy rule — a typo'd redaction rule refuses to
evaluate rather than passing.

## Both implementations

The rule is implemented in the reference verifier **and** in the
[independent JavaScript verifier](PORTABLE.md) in the same unit — a format
change only one implementation understands would undo the
cross-implementation guarantee. Both report the same withheld count and
the same exit code, and neither can report a pass on a redacted bundle.

## Honest limits

- **The `result` section is never redacted.** The claims are the finding
  being shared; removing them would leave nothing to verify. Evidence a
  claim *cites* therefore remains visible in the claim's own support —
  what redaction removes is the far larger **uncited** corpus. If the
  cited evidence itself cannot be shared, the receipt cannot be shared.
- **Ids remain visible**, by necessity (see above).
- Redaction is not encryption and not a zero-knowledge proof: it withholds
  content and proves *what was withheld*, nothing about it.
- A redacted bundle is weaker on purpose. If you need a full PASS, send
  the complete bundle — or ask for one with a policy.
