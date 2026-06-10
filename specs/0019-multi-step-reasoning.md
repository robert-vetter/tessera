# 0019. Multi-step reasoning (compare + superlative)

- **Phase / milestone:** Phase 2 — multi-step reasoning across several entities
  and both modalities
- **Issue:** (none)
- **Status:** implemented

## Problem

Phase 1 answers one entity at a time. Phase 2's roadmap requires *multi-step
reasoning across several entities*: questions whose answer is computed from
intermediate, per-entity results. This unit adds the two honest, deterministic
multi-step shapes the data supports: **compare two named entities'** total net
order value, and a **superlative ranking** ("which entity has the highest total
net order value in EUR?"). Every intermediate step is a sourced claim; the
conclusion is a new claim shape the faithfulness verifier learns to recompute
**in lockstep** — otherwise the gate would either pass unverified claims or
fail honest ones.

## Acceptance criteria (decided, not asked — autonomous mode)

- [ ] `reasoning.py` with `reason(question, graph) -> Answer`:
      - **Compare:** two entities found by relative-threshold name containment
        (≥ 60 % of the normalized name, ≥ 6 chars — the absolute-only threshold
        sweeps in generic tokens like "logistik"); per-entity sourced aggregate
        step claims + one conclusion claim citing both row sets; **refuses** to
        compare across currencies or with a mixed-currency entity.
      - **Superlative:** requires an explicit currency scope ("… in EUR");
        ranks per-entity totals over that currency's rows only (no silent
        cross-currency mixing); conclusion claim cites the winner's rows.
        Without a scope, **refuses**, naming the currencies present.
      - Anything else: principled refusal (the router, Unit 2, owns dispatch).
- [ ] `eval/metrics.py` verifies both conclusion shapes by **recomputation over
      the graph** (entity totals re-derived from sold_to edges + clusters), with
      adversarial tests proving each new shape can fail (wrong winner, wrong
      amount, wrong entity count).
- [ ] Existing per-entity aggregate claims keep verifying via the existing
      shape; gate + eval stay green (faithfulness 1.000 floor).

## Scope

**In:** the two reasoning shapes, verifier extension, tests. **Out:** routing
(Unit 2), LLM/NLU (ADR 0006), arbitrary aggregation grammars, conversational
follow-ups (Phase 4).

## Eval impact

Faithfulness floor now also covers multi-step conclusions (provably fallible —
adversarial tests). Coverage/quality unchanged this unit; synthetic cases over
these shapes arrive in Unit 4 (spec 0022).

## Risks

- Conclusion-claim verification needs the graph; `is_supported` gains an
  optional `graph` parameter (backward compatible).
- Name containment can still miss heavily-abbreviated references — an honest,
  documented limit; ER improvements are Unit 6 / ADR 0004 territory.
