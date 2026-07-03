# 0007. Synthetic eval scenarios: enumerated from the graph, expectations from data

- **Status:** accepted (2026-06-10)
- **Phase:** 2

## Context

The roadmap requires synthetic data generation feeding the harness, including
deliberately tricky cases (ambiguous entities, missing evidence, conflicting
sources). Seven curated gold cases anchor the metrics but cannot scale; the
danger of *generated* cases is **tautology** — if the generator derives its
expectations by running the engine, the eval passes by construction and the
number is decorative (exactly what CLAUDE.md forbids).

## Decision

`tessera.eval.synthetic` **enumerates cases from the knowledge graph's
content** — deterministically, no RNG, no LLM:

- per-entity lookup and aggregate questions for every resolved entity;
- multi-step compare cases over consecutive same-currency entity pairs and a
  superlative case per currency;
- refusal cases: ambiguous shared-name-token questions, missing-evidence
  questions from fixed out-of-corpus templates, and the unscoped-superlative
  currency-mixing refusal.

**Expectations are computed from the data** (record ids; totals re-derived
with Decimal arithmetic from graph attributes), never from engine output. The
engine appears in generation only as a *well-posedness filter*: a candidate
question is emitted only if entity-name matching identifies exactly the
intended entities (skipping, e.g., the deliberately unresolved Globex variant
family, where naming one entity is inherently ambiguous).

Gold and synthetic results are **reported separately** (gold stays the
human-checked anchor; synthetic measures scale), and the faithfulness floor
gates **both**.

## Consequences

- The synthetic battery grows automatically with the data; an engine
  regression breaks real, data-derived expectations rather than echoes.
- Generator filtering means the battery only contains questions the current
  matcher considers well-posed — a documented blind spot: *phrasings* the
  rules cannot parse are exercised by the refusal templates and by gold, not
  by generated paraphrases.

## Revisit triggers

1. ADR 0006 trigger 1 fires (rule routing/parsing misses real phrasings) —
   add paraphrase variants, possibly LLM-generated *offline and committed*,
   so CI stays deterministic.
2. The synthetic battery saturates (every case passes for two consecutive
   phases) — add harder generated shapes (multi-hop joins, doc+row conflicts).

## Alternatives considered

- **LLM-generated cases at eval time** — rejected: nondeterministic CI, keys
  in the gate, and unauditable expectations.
- **Random sampling with a seed** — rejected: enumeration is just as
  deterministic and easier to audit (every entity appears; no sampling bias).
- **Engine-derived expectations** — rejected as tautological (see context).

## Addendum (2026-07-03, spec 0122)

The benchmark unit's adversarial review sharpened a distinction this ADR
left implicit. "Expectations never from engine output" holds for expected
**values** everywhere: every number, count, id, and entity name in a
synthetic expectation is recomputed from the ingested data at eval time,
never read back from the engine. Expected **phrasing** differs by battery:
the business generator's compose-case facts are written in the engine's own
render templates ("Total net order value across …", "is one resolved
entity", "Refused to sum across …"), while the devex/github_actions
generators phrase facts as plain record text. For the eval's own purpose —
regression against the measured engine — the template phrasing is
appropriate and non-tautological (the *values* inside the templates are
data-derived, so a computation regression still fails). But it makes those
cases **definitionally unwinnable for any answerer that does not compose in
the engine's words**, which matters the moment the cases are reused
comparatively. The Faithfulness Floor benchmark (spec 0122,
`docs/BENCHMARK.md`) therefore computes and publishes this boundary per
battery ("reachable Q" in its structural notes) instead of letting the
quality gap read as purely empirical. Any future battery should prefer
record-reachable phrasing where the case's point is not the composition
itself.
