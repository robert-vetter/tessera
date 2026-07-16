# The challenge — spot the lie

*Milestone 22 (spec 0140). Two trust bundles ship in this repo. One is
honest. One is a cryptographically perfect fake. Tell them apart offline.*

Download the two files (they are committed):

- [`data/challenge/honest.tsb`](https://github.com/robert-vetter/tessera/blob/main/data/challenge/honest.tsb)
- [`data/challenge/forged.tsb`](https://github.com/robert-vetter/tessera/blob/main/data/challenge/forged.tsb)

Both answer the same question — *"Compare Müller Logistik and Nordwind
Logistik totals"* — over the same synthetic business corpus. The forged
one inflates a customer's stated total by EUR 3,500 while leaving **every
cited sales record untouched**: a confident, well-sourced, *wrong* answer,
exactly what an ungated agent produces. It is re-sealed, so its hash chain
is valid.

## Integrity checking cannot tell them apart

Both bundles are re-sealed, so the check that hash-chain and Merkle-receipt
systems perform — "was this file altered since it was sealed?" — passes
**both**:

```console
$ uv run python scripts/foil_integrity_only.py data/challenge/honest.tsb
INTACT — every hash checks out. (Nothing here checked the content.)
$ uv run python scripts/foil_integrity_only.py data/challenge/forged.tsb
INTACT — every hash checks out. (Nothing here checked the content.)
```

(These two are unsigned so they stay byte-reproducible from the committed
script. A **signature** would not help either: it proves *who* sealed a
file, not whether its content is true — sign both with the same key and
both signatures verify, while one still lies. That is exactly the point;
see the [honest limits](BUNDLE.md#honest-limits).)

## Re-execution can

`tessera verify` re-runs the verification offline — it re-sums the cited
rows and re-derives every claim:

```console
$ uv run tessera verify data/challenge/honest.tsb
…
verdict:   PASS (exit 0)

$ uv run tessera verify data/challenge/forged.tsb
…
semantic:  RE-DERIVED — 1/3 recorded claim verdict(s) re-executed and matched
  [!!] claim 0: UNSUPPORTED — 'Nordwind Logistik GmbH': total net order value across 3 order(s): EUR 88,000.00.
  [!!] claim 2: UNSUPPORTED — 'Nordwind Logistik GmbH' (EUR 88,000.00 across 3 order(s)) exceeds 'Mueller Logistik Gmbh' …
answer:    DOES NOT RE-DERIVE …
verdict:   FAIL (exit 2)
```

The cited rows sum to EUR 84,500, not the stated 88,000 — so the claim
that rests on them fails, and it names itself. `tessera bundle explain
data/challenge/forged.tsb` shows the same chain a human can read.

**This runs on an air-gapped laptop.** No network, no engine cache, no
trust in whoever produced the file. That is the whole point: the verdict
is a recomputation a third party re-runs to the same answer.

## The forgery hides nothing

`scripts/forge_challenge_bundle.py` is committed and deterministic — it
builds the honest bundle and derives the forgery by one documented edit,
so anyone can re-run it and confirm exactly how the fake was made. A test
pins that the committed files are byte-identical to a fresh run, so the
forgery can never drift from the script that explains it.

## What about an LLM-as-judge? (an honest one-shot)

The other common way to "check" an answer is to ask a second language
model whether it looks faithful to its sources (RAGAS, DeepEval, and
similar are this, at scale). We ran exactly that on the forged bundle —
Claude as a faithfulness judge, the same "is this statement supported by
this context?" task — and report what actually happened, because the
result is more interesting than the slogan:

- Given the cited rows **clearly attributed to the customer**, a capable
  model re-added the small (3–5 row) sums correctly: it rejected the
  inflated total (*"24,000 + 22,000 + 38,500 ≠ 88,000"*) and accepted the
  honest one. On this toy scale the judge is **not** fooled by the
  arithmetic.
- But given the *same* cited rows **without** that attribution, the same
  judge rejected the honest, true claim with 0.95 confidence — a false
  negative — on entity-linking grounds unrelated to any forgery.

So the honest finding is not "an LLM judge is easily fooled." It is that
an LLM judge's verdict **depends on how the context is framed, is not
deterministic, and comes with no recomputation you can re-run** — the same
claim earned opposite verdicts. A trust gate cannot rest on that, and it
does not scale: re-summing three rows is easy; a real enterprise aggregate
is hundreds of rows across joins, where an LLM's arithmetic degrades and a
`Decimal` recomputation does not. Tessera's verdict is the recomputation —
identical, offline, re-runnable by anyone. Reproduce it:

```console
$ set -a; source .env; set +a   # ANTHROPIC_API_KEY
$ uv run python scripts/llm_judge_contrast.py
```

The model and the exact prompt are in the script; this is one recorded
measurement, not a CI-gated claim.

## Build a better forgery

The real invitation: make a `.tsb` that is **false** but that
`tessera verify` passes. If you find one, that is a genuine finding —
open an issue. The scope is honest and worth stating: the claim is
offline re-execution of *claim-vs-evidence* faithfulness over the
packaged corpus (the [honest limits](BUNDLE.md#honest-limits) apply); it
is not a claim about truth in the world, and the challenge corpus is
synthetic (no gated data ever ships in a downloadable bundle).
