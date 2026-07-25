# The Verification Gap — a conformance benchmark you can re-run

*Milestone 22 (spec 0146, ADR 0036). One command grades the published
agent-receipt verification methods of 2026 against an attack battery,
under two named threat models.*

```console
$ uv run tessera conformance
```

This project's positioning has always rested on a comparative claim:
*integrity is solved; content is not checked.* An assertion is what every
vendor has. This is the measurement.

> **What is graded, and what is not.** The methods below are **our own
> implementations of publicly described methods**, committed in
> [`src/tessera/conformance/methods.py`](https://github.com/robert-vetter/tessera/blob/main/src/tessera/conformance/methods.py)
> and written to be as strong as their sources describe. **No third-party
> product is run, named in a score, or characterised beyond what its own
> published description says about itself.** Every number here is
> reproducible from a clean clone, offline.

## Read this table first: the outside tamperer

If the attacker is someone *other than the issuer* — a tampered file in
transit or at rest, no signing key — then **signatures are sufficient**.
Any change moves the root and cannot be re-attested. Re-execution adds no
detection power in this model, and Tessera does not win it.

| method | envelope | semantic | action | chain | declaration | authorization | total |
|---|---|---|---|---|---|---|---|
| hash-manifest | 2/3 | 0/7 | 0/5 | 0/3 | 0/2 | 0/1 | **2/21** |
| signed-receipt | 2/3 | 7/7 | 5/5 | 3/3 | 2/2 | 1/1 | **20/21** |
| policy-bound-receipt | 2/3 | 7/7 | 5/5 | 3/3 | 2/2 | 1/1 | **20/21** |
| syntactic-envelope | 2/3 | 7/7 | 5/5 | 3/3 | 2/2 | 1/1 | **20/21** |
| re-execution (Tessera) | 3/3 | 7/7 | 5/5 | 3/3 | 1/1 | 0/1 | **19/20** |

## Now the model that actually applies: the issuer

An agent's receipt is sealed by the party whose honesty is in question.
When the forgery is produced *inside* the trust boundary — a self-serving
operator, a compromised key, or simply an agent pipeline sealing its own
output — every signature still verifies, because the forgery is signed
with a legitimate key.

| method | envelope | semantic | action | chain | declaration | authorization | total |
|---|---|---|---|---|---|---|---|
| hash-manifest | 2/3 | **0/7** | **0/5** | **0/3** | 0/2 | 0/1 | **2/21** |
| signed-receipt | 2/3 | **0/7** | **0/5** | **0/3** | 0/2 | 0/1 | **2/21** |
| policy-bound-receipt | 2/3 | **0/7** | **0/5** | **0/3** | 1/2 | 0/1 | **3/21** |
| syntactic-envelope | 2/3 | **0/7** | **0/5** | **0/3** | 0/2 | 1/1 | **3/21** |
| re-execution (Tessera) | 3/3 | **7/7** | **5/5** | **3/3** | 1/1 | 0/1 | **19/20** |

**Zero.** Not "fewer" — zero semantic, action and chain forgeries detected
by any method that does not re-execute the content. That is not an
implementation weakness that a better hash could fix: a verifier that
never recomputes the claims against the evidence cannot notice that the
claims stopped following from the evidence. It is structural.

## Where Tessera loses — and why that column stays

A benchmark whose author never loses a cell is not a benchmark.

- **`stale_contract_replay`** — an honest, byte-perfect receipt whose
  governing mandate has expired, replayed as current. Re-execution
  **misses it, by design**: a PASS is a statement about claims and
  evidence, never about recency (a limit recorded in
  [BUNDLE.md](BUNDLE.md) since the M20/M21 audit). The
  runtime-attestation method catches it with a contract-freshness
  invariant. Different axis, honestly scored.
- **`policy_swap`** is scored **not applicable** to re-execution — not as
  a win. Tessera keeps policy *outside* the artifact by design
  ([ADR 0034](adr/0034-trust-policies.md)), so an in-receipt policy swap
  cannot exist against it. Impossible attacks are never counted.
- Under the outside-tamperer model, re-execution's total (19/20) is
  *lower* than the signature-based methods' (20/21). Printed first, on
  purpose.

## The methods, and the sources they model

| method | models | scope its source claims |
|---|---|---|
| `hash-manifest` | hash-chained audit logs, Merkle evidence bundles | the record was not altered |
| `signed-receipt` | IETF ASQAV signed action receipts (2026 draft) | the receipt is authentic and unaltered, checkable offline |
| `policy-bound-receipt` | Microsoft Agent Governance Toolkit, *Independently Verifiable Compliance Receipts* | signature validity, chain integrity, and the declared policy hash matching the expected one — the proposal states its verifier confirms consistent signing, not that the decision was correct |
| `syntactic-envelope` | *Proof of Execution*, Rhodes & Kang, [arXiv:2607.05397](https://arxiv.org/abs/2607.05397) (2026) | authorization, scope containment, trace integrity and replayability, via invariants the paper itself calls syntactic predicates |
| `re-execution` | this project | claim-vs-evidence faithfulness and approval-gated action — *not* truth in the world, not execution attestation |

**On Proof of Execution specifically.** It is the closest work to this
project and it is strong at what it claims. Its validator checks
syntactic invariants over a contract, an event stream and a replay
context; its envelope-closure invariant is scoped to checking that the
*declared* envelope is consistent, with undeclared dependencies placed
outside that scope; and its deterministic-replay guarantee rests on
stated deployment assumptions rather than on the validator recomputing
content. That is a **different axis** from claim-vs-evidence checking,
which is why this benchmark grades it on the axis it targets
(`authorization`, where it wins the cell Tessera loses) and why the
project's own claim is stated narrowly: Tessera re-executes *claims
against evidence*, not execution traces.

## Signatures are not the gap — issuance is

The reflex objection is "just sign the receipt." The T1 table shows that
this works, completely, against outside tampering. It does nothing about
the case the industry actually has: the model, the agent framework, and
the receipt issuer are all inside the same trust boundary, and the
question an auditor asks is not *"did someone else alter this?"* but
*"is what this thing said actually supported by what it cited?"* A
signature answers the first question. Only re-execution answers the
second.

## Honest limits of this benchmark

- It measures **detection of these 21 attacks on this artifact format**.
  The structural conclusion generalises — a method that never re-executes
  cannot detect a re-sealed semantic edit — but that is stated as an
  *argument*, not as data.
- The reference implementations are faithful to *published descriptions*,
  not to any shipped product's actual code. A vendor whose product does
  more than its published method describes would score higher; that is
  why nothing here is attributed to a product.
- Signatures are modelled as an unforgeable attested root rather than by
  running real Ed25519 — which is exactly the property a signature
  provides ([ADR 0032](adr/0032-bundle-signing.md)) — so the benchmark
  stays key-free and runnable on a clean clone.
- LLM-judge "verification" is not in this table: it is non-deterministic
  and un-re-runnable, and was measured separately (and honestly) in
  Milestone 22's one-shot.
- The battery inherits Tessera's own scope: it says nothing about whether
  an answer is *true in the world*, only whether it follows from the
  evidence packaged with it.

## Reproduce it

```console
$ uv run tessera conformance            # the tables above
$ uv run tessera conformance --json     # machine-readable scorecard
```

The committed scorecard lives at `data/conformance/scorecard.json` and a
test pins it byte-identical to a fresh run, so a published number can
never drift away from the code that produced it. Adding a method or an
attack is additive — and any change to these numbers shows up in review.
