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
