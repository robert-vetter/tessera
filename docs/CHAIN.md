# Chained bundles — the audit trail for agent pipelines

*Milestone 22 (spec 0143, ADR 0033). A verified bundle becomes evidence
for the next answer; one offline `verify` re-executes the whole chain.*

Agent systems in production are pipelines: one agent's output is the
next agent's input. A single trust bundle attests a single decision —
but what travels *between* agents is unverified text, so a pipeline's
audit trail breaks exactly at the hand-offs. `tessera bundle chain`
closes that gap with the same primitive the single bundle rests on:
**re-execution, now recursive.**

```console
$ uv run tessera bundle "Why did run R-1042 fail, and has this happened before?" \
    --domain devex -o rca.tsb
$ uv run tessera bundle chain \
    "What do the verified receipts establish about the run R-1042 failure \
     and the Müller Logistik and Nordwind Logistik totals?" \
    rca.tsb data/challenge/honest.tsb -o brief.tsb
outcome: grounded — 5/5 claim(s) verified
chain:   2 upstream bundle(s) embedded, re-verified

$ uv run tessera verify brief.tsb
…
chain:     2/2 embedded upstream bundle(s) re-verified recursively
  [ok] upstream sha256:0ecaeaff0deb…: PASS
  [ok] upstream sha256:5cc23099dccc…: PASS
answer:    re-derives — the packaged corpus yields exactly this answer for this question
verdict:   PASS (exit 0)
```

A committed, deterministic demo brief lives at `data/chain/brief.tsb`
(built by `scripts/build_chain_demo.py`; a test pins byte-identity, the
[challenge](CHALLENGE.md)'s no-drift pattern). It chains a DevEx
root-cause receipt with the challenge's honest business bundle — two
verticals, one verifiable brief.

## What the chain rules are

- **Cite only what re-verifies.** Emission runs the full verifier on
  every upstream; a bundle that does not PASS refuses to chain (try it:
  chaining `data/challenge/forged.tsb` is refused with the reason). Only
  verifier-passing claims become evidence records.
- **Upstreams travel embedded.** The chain's integrity manifest carries
  one leaf per upstream, named by its root — the chain root commits to
  the upstream set *and* bytes, and the file stays self-contained.
- **Verification recurses; nothing is taken on record.** `verify`
  re-verifies every embedded upstream with the full verifier, requires
  every derived record to byte-match the upstream claim it cites (and
  that claim to re-derive in the upstream's own re-execution), and
  re-runs the chain's deterministic answer route over the packaged
  corpus. Chains can cite chains; cycles are impossible (embedding needs
  the upstream's final sealed bytes, so no bundle can contain its own
  root).

## Why forging a chain is not easier than forging a link

Tamper a byte anywhere — including inside an embedded upstream — and the
envelope breaks (exit 4, the changed leaf named). Re-seal everything
consistently at every level, and the semantic layer takes over: the
strongest attacker, who swaps in an internally-consistent forged
upstream and rewrites every chain-level reference to match, produces a
bundle whose own answer re-derives and whose citations all byte-match —
and it still FAILS, because the embedded upstream's claims do not
re-derive from their own packaged evidence. That exact attack is a
pinned test (`test_deep_forge_is_caught_by_recursion_alone`).

> To forge a chain you must forge one link's own re-execution — and the
> [challenge](CHALLENGE.md) exists to show you cannot.

## Honest limits

- The chain answer **cites** upstream findings (verbatim, with the
  upstream root and claim index in each record's provenance); it
  computes nothing new. Cross-bundle aggregation or synthesis is future
  work, not smuggled in.
- Chains verify **Tessera bundles**. External agents participate by
  exchanging bundles (CLI or MCP); this is not a verification surface
  for arbitrary agent output ([ROADMAP3](ROADMAP3.md), "What Act 3 will
  NOT do").
- A chain claim's grammar is *citation*: the chain level proves "this is
  byte-for-byte what the upstream's verifier-passing claim says"; the
  *truth* of that claim relative to raw evidence is re-established by
  the recursive upstream re-execution, one level down — which is where
  that evidence lives. [BUNDLE.md's honest limits](BUNDLE.md) apply to
  every link.
- Embedded upstreams grow the file: the demo brief is ~573 KB (a 147 KB
  DevEx receipt + the 404 KB business bundle + the derived corpus).
- The Auditability Floor's mutation battery does not yet include
  cross-bundle classes; the chain attack classes are pinned in
  `tests/test_bundle_chain.py` (spec 0143 names the floor extension as
  future work).
