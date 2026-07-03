# Show HN — draft (publish under the maintainer's account, his timing)

*Numbers verified 2026-07-03 against `uv run tessera-benchmark`; re-run and
re-check every number before publishing. The CI-pinned public source is
[docs/BENCHMARK.md](../../docs/BENCHMARK.md) — the post links there, never
duplicates beyond the headline.*

**Prereqs before posting:** hosted demo warm (open the HF Space once — it
sleeps after ~48h idle); README current; registry submission ideally live
(RUNBOOK). Post morning US-Eastern, Tue–Thu. Stay in the thread for the
first 3–4 hours and answer everything.

## Title (75/80 chars)

Show HN: Tessera – an evidence gate for AI agents (provenance + receipts)

## URL

https://github.com/robert-vetter/tessera

## Text

Last July an agent at Replit deleted a production database during a code
freeze, fabricated data to cover it, and misreported the rollback. The
post-mortem consensus — dry-runs, approval gates, blast-radius previews —
is what I've been building as an open-source layer, with one addition the
industry keeps skipping: the agent's *statements* need gates too, not just
its actions.

Tessera is a deterministic evidence layer that sits between an agent and
your data:

- Every answer is composed of claims, and every claim carries a provenance
  trail to specific source records (a table row, log lines, a document
  span). A deterministic verifier re-checks each claim against exactly the
  records it cites — recomputing aggregates, not pattern-matching prose.
- No supporting evidence → an explicit refusal, not a guess. Ambiguous
  entity, conflicting sources, incomparable currencies → refusal with the
  reason.
- Actions are drafted only from verifier-passing claims; the exact wire
  request (e.g. the GitHub POST body) is previewed before anything happens;
  execution sits behind approval and returns a receipt. Over MCP, so any
  agent can use it as its evidence oracle.
- Faithfulness is a number in CI, not a vibe: a hard 1.0 floor (an
  unsupported claim fails the build), and it has genuinely failed before —
  that's the point.

What I'd want you to poke at: the benchmark. I ran the engine's own
retrieval layer *ungated* (BM25 top-5, recite verbatim, always answer) as a
baseline against the gated engine — same corpora, same questions, same
verifier. The ungated baseline scores 1.000 per-claim "faithfulness"
(recitation trivially passes a containment check!) while producing
trustworthy outcomes on 0–25% of cases — it answers questions it should
refuse and can't state what the evidence adds up to. The per-case results,
the structural notes that say exactly which part of that gap is
definitional (the benchmark computes its own boundary), and the "how to
attack this" section are in docs/BENCHMARK.md; CI regenerates the tables on
every build so the published numbers can't drift from the code.

Honest limits, so you don't have to dig for them: no LLM anywhere in the
trust path (an optional model can narrate answers; it never attests — and
the flip side is the answer layer is deterministic machinery, not
open-ended NL understanding); the eval corpora are mine (two synthetic
verticals + this repo's real CI history); BYO is measured on exactly two
external repos (astral-sh/uv, simonw/llm) plus a CSV corpus, and the
per-repo `smoke` battery exists precisely because your repo may surface a
gap — on one third repo it did, and said so instead of answering.

Try it: live demo (read-only, simulated actions) at
https://robert-vetter-tessera.hf.space — or on your own CI failures in ~20
seconds after clone: `uv run tessera connect github <owner>/<repo>` then
`uv run tessera ask <owner>/<repo> "Why did run <id> fail?"`.

MIT. I'd especially value: attacks on the benchmark methodology, repos
where `smoke` fails, and whether the evidence-gated-action shape fits how
you're deploying agents.

## Planned first comment (post immediately after submitting)

Author here — some context on what this is NOT, since "trust layer" is a
crowded phrase: it's not an MCP gateway (those gate on identity/permissions;
this gates on evidence), not a guardrails/policy engine (a perfectly "safe"
hallucination passes those), and not an LLM-judge eval (the verifier is
deterministic and runs in CI). The unusual combination is per-claim
provenance + evidence-gated actions with receipts + a benchmark you can
re-run offline. Happy to go deep on the verifier's claim grammars, the
non-destructive entity resolution, or where the deterministic line genuinely
hurts (semantic phrasing misses are kept visible at 0.950/0.833 coverage
offline rather than papered over).

## Known-attack prep (answers ready; concede fast, never defend past the data)

- **"The baseline is a strawman."** It's the engine's own retrieval, scored
  by the same verifier with the same claim grammars; where recitation
  suffices it gets full marks (see the per-case table — it wins four gold
  cases). The gap is attributable to the gate, not a weakened retriever.
- **"Expected facts are phrased by you — circular."** Partially true, and
  the artifact computes exactly how much instead of hiding it: the
  generated block's *structural notes* publish per-battery "reachable Q"
  counts — business synthetic is 0/45 reachable, so that row's 0.038 is a
  structural ceiling, and the doc says so in bold. Coverage and refusal
  columns are phrasing-independent throughout. Where phrasing is plain
  record text (devex synthetic, 10/10), the baseline earns 0.583. The doc
  disclosed this before you found it; add record-phrased cases and re-run —
  that's the invited attack.
- **"Deterministic = it can't understand my question."** Correct, and
  refusal is the designed behavior at that boundary; the router's ceiling
  is documented with committed specimens (ADR 0006).
- **"Synthetic corpora prove nothing."** The github_actions battery is real
  CI data including a real un-planted miss (coverage 0.000 when first
  measured) that was closed deterministically; the whole trail is in
  eval/history.jsonl.
- **"Why not just use the model's citations?"** Model-emitted citations
  assert; nothing re-checks them. Here the verifier recomputes claims
  against the cited records, and a claim outside the checkable grammars
  cannot ship.
- **"Receipts are just logs."** A receipt links the executed request to the
  approved preview to the claims to the evidence records — it's the chain,
  not the log line. And the system that wrote it holds no credential on the
  public surface (`sent: false` by construction there).
