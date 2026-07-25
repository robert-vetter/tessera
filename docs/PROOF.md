# The bounded soundness theorem — machine-checked, exhaustively

*Milestone 22 (spec 0147, ADR 0037). Everything else in this project
measures. This proves — within a bound that is printed next to every
result.*

```console
$ uv run tessera proof
```

A mutation battery answers *"did any of the attacks we thought of get
through?"* It cannot answer *"could an attack nobody thought of get
through?"* This does:

> **Theorem (bounded).** For every state `S` in the enumerated universe:
> if the verifier returns **PASS** for `S`, then `S` is **honest** — every
> claim's asserted content is derivable from the evidence it cites, every
> recorded verdict equals the recomputed one, and the recorded answer is
> exactly the one the packaged corpus yields for the packaged question.

**461,544 states. Every one of them. Not a sample.**

| universe | bound | states |
|---|---|---|
| A | ≤3 records, values 1–4, 1 claim, asserted 0–12 | 91,104 |
| B | ≤2 records, values 1–3, 2 claims, asserted 0–6 | 370,440 |

| verifier | result | states accepted |
|---|---|---|
| **re-execution** (Tessera's model) | **PROVED — no false PASS exists** | 204, all honest |
| control: trusts the recorded verdict | **REFUTED** (as required) | 139,044, incl. forgeries |
| control: claims only, no answer re-derivation | **REFUTED** (as required) | 5,160, incl. forgeries |

Fidelity: **26,840** model claims re-evaluated by the *shipping*
`is_supported` with the real business claim grammars — **0 disagreements**.

## Why "exhaustive" is not a figure of speech

The checker does not apply attacks. It walks **every state in the
universe** and checks the implication. Because the universe is closed
under arbitrary rewriting, an attacker with unlimited re-sealing and
re-signing power can only ever produce a state that is *already in it* —
so attacker coverage follows as a corollary, and no argument about the
completeness of an attack list is needed. Enumeration over a finite domain
is a decision procedure; that is what makes this a proof for the domain
rather than a very thorough test.

The model gives that attacker **maximum power**: it contains no hashes and
no signatures at all. Anything that could be re-sealed is assumed already
re-sealed. It is the conformance benchmark's *issuer* threat model taken
to its limit.

## Why you should believe the word "PROVED"

Because the same run has to produce two **REFUTED**s, and it prints their
counterexamples:

- **The trusting control** believes the recorded verdict instead of
  recomputing it — precisely what an integrity-only receipt does once its
  hashes check out. Counterexample: a corpus holding `[1]`, a claim
  asserting the total is `0`, marked verified. It passes. It is a lie.
- **The claims-only control** recomputes every claim honestly but never
  checks that the recorded answer is the one the corpus yields.
  Counterexample: a *true* statement attached to the wrong question.

`proved` is *defined* to require both refutations plus zero fidelity
disagreements, so a checker that quietly lost its ability to detect
unsoundness reports **NOT PROVED** rather than a vacuous success. Two more
guards sit underneath: the universe size is computed by formula *and* by
walking, and the run aborts if they disagree (a silently truncated
enumeration would make the theorem vacuous); and the verifier must accept
at least one state, because rejecting everything is trivially sound and
worthless.

That last guard earned its keep during the build: the first cut of
universe B fixed answers at exactly two claims while every canonical
answer had one — so *nothing* passed and the theorem held there only
vacuously. The test caught it; the model gained a genuine two-claim
question and the universe now enumerates answers of every length.

## What this does **not** prove

- **It is bounded.** 1–2 claims, ≤3 records, small value domains. Larger
  states are not covered. The bound is printed with every result and
  committed in the certificate.
- **It is not a proof about the Python implementation.** It proves a
  property of a model whose *claim semantics* are differentially checked
  against the shipping verifier over the same domain. Hashing, JSON
  handling, I/O and everything else in the implementation are out of
  scope. A proof-assistant formalisation of the real code is named future
  work, not a promise.
- **Model fidelity is tested, not proven.** That gap is inherent to this
  technique; naming it is the difference between a result and a slogan.
- **It says nothing about truth in the world.** Honest here means *a claim
  follows from the evidence packaged with it* — the same scope the whole
  project carries.

## How it composes with the rest

[The Verification Gap](CONFORMANCE.md) *measured* that integrity-only
methods detect none of the semantic forgeries when the issuer is the
forger. This proves the other half: for the re-executing verifier, in a
bounded domain, such a forgery **cannot exist** — and the trusting control
in this proof is the same method the benchmark grades, refuted here from
first principles rather than by example.

## Reproduce it

```console
$ uv run tessera proof              # ~1 second
$ uv run tessera proof --json       # machine-readable certificate
$ uv run tessera proof --deep       # adds a 3-claim universe (~4.4M states)
```

The certificate is committed at `data/proof/certificate.json` and pinned
byte-identical to a fresh run, so a published theorem can never drift from
the code that produced it. Widening a bound is a one-line change with a
visible cost in the certificate — the claim grows with evidence, not with
rhetoric.
