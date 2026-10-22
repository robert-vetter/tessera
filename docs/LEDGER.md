# The issuance ledger — "is this all of them?"

*Milestone 22 (spec 0151, ADR 0041). Ten layers prove a receipt is honest.
This one addresses the question they cannot: whether you were shown
everything.*

Every guarantee in this project so far concerns a receipt you were
**given**. An operator who simply does not show you a decision defeats all
of them at once — not by breaking anything, but by omission. That is the
completeness axis, and it is what transparency logs exist for.

```console
$ uv run tessera bundle attest decision.tsb --ledger var/ledger/issued.log
recorded: entry 41 of 42 in var/ledger/issued.log
head:     42:sha256:7abb4df2fb3a…
wrote:    decision.tsb.inclusion.json
note:     a verifier checks this against a head they already had — the
          proof never vouches for its own head.

$ uv run tessera verify decision.tsb --inclusion decision.tsb.inclusion.json \
    --head 42:sha256:7abb4df2fb3a…
verdict:   PASS (exit 0)
ledger:    included in the issuance log at the head you supplied
```

And the decision that was never recorded:

```console
$ uv run tessera ledger prove sha256:9ebb66f3ae04…
error: sha256:9ebb66f3ae04… is not in this log — no inclusion proof exists
       for a receipt that was never recorded
```

## What the two proofs do

| proof | question it answers |
|---|---|
| **inclusion** | is this receipt in the log, at the head *you already hold*? |
| **consistency** | does the current head extend an earlier one **without anything rewritten**? |

Consistency is what turns "append-only" from a promise into a property:
an operator who edits or drops an earlier entry cannot produce a proof
that reconstructs both heads. Correctness is established **exhaustively**
in the test suite — every entry of every log size and every consistency
pair up to 40, plus rewrite, deletion, truncation and padding attacks.

The construction is Certificate Transparency's (RFC 6962), including
domain-separated hashing (`0x00` for leaves, `0x01` for nodes) so a leaf
can never be replayed as an interior node.

## Nothing in the bundle changes

Attestation emits a **detached** proof, exactly like an
[approval](APPROVAL.md): no bundle byte moves, no root changes, and every
existing signature, approval and committed artifact stays valid. The
reserved `anchor` section remains reserved for the public-log unit.

A policy can require the proof, fail-closed:

```json
{ "rules": { "ledger": { "require_inclusion": true } } }
```

Not supplying a proof is a violation, not a pass — and `verify
--inclusion` without `--head` reports *not checked* rather than implying
it checked something.

## The bound, stated with the guarantee

A local log proves **inclusion against a head you already hold** and that
**history was not rewritten** for anyone who has seen an earlier head. It
does **not** prove completeness of the world:

> An operator who keeps *two* logs can show two parties two different
> heads, and no offline check detects that split view.

Closing that requires heads to be unforgeably public, which is what a
public transparency log does — the reserved unit that needs the
maintainer present, because publishing is irreversible and
identity-bearing. Until then the honest framing is: **every head anyone
has ever seen constrains the operator from that moment on.** Publishing a
head periodically — in a report, an email, a commit — is therefore a
meaningful act, and each one narrows the room to rewrite.

## Both implementations

Inclusion verification lives in the shared verifier core, so the CLI, the
cross-implementation kit and the browser page all understand it. A
protocol addition only one implementation understood would undo the
guarantee established in [PORTABLE.md](PORTABLE.md); a differential test
checks Python and JavaScript agree on the same proofs, including the ones
that must be refused.
