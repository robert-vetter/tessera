# 0022. Synthetic eval scenarios feeding the harness

- **Phase / milestone:** Phase 2 — synthetic data generation incl. tricky cases
- **Issue:** (none)
- **Status:** implemented

## Problem

Seven gold cases anchor the trust metrics but cannot stress the engine at any
scale, and the roadmap explicitly requires synthetic generation covering the
tricky cases: ambiguous entities, missing evidence, conflicting sources. The
design question is how to generate cases whose passing *means something* —
see ADR 0007 (enumerate from the graph; expectations from data, never from
engine output; engine used only as a well-posedness filter).

## Acceptance criteria (decided in autonomous mode)

- [ ] `tessera.eval.synthetic.generate_cases(graph)` — deterministic (no RNG,
      no LLM), producing routed cases: per-entity lookups, per-entity
      aggregates (expected totals re-derived with Decimal from graph
      attributes), consecutive-pair compares, a superlative per currency, and
      refusal cases (ambiguous shared token, missing evidence, unscoped
      superlative).
- [ ] Harness scores gold and synthetic **separately** (`EvalReport` carries
      both); the CLI prints both; the faithfulness floor gates both.
- [ ] Ill-posed candidates (e.g. the unresolved Globex family, where a name
      matches several clusters) are filtered out, and the filter itself is
      tested.
- [ ] Battery size and composition asserted in tests (loudly changes when the
      data changes); whole suite + eval green.

## Scope

**In:** generator, harness/CLI reporting split, tests. **Out:** LLM/random
generation (ADR 0007), committed case files (generated in memory at eval
time), paraphrase stress (ADR 0007 trigger 1).

## Eval impact

Adds a second, larger measured battery (~dozens of cases). Faithfulness floor
now spans both sets. Synthetic coverage/quality become new honest numbers —
they may be < 1.0; that is signal, not failure (only the faithfulness floor
gates).

## Risks

- Tautology (mitigated per ADR 0007); generator blind spot for unparseable
  phrasings (documented there).
