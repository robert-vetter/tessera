# 0020. Question routing (one door, explainable dispatch)

- **Phase / milestone:** Phase 2 — routing distinguishes simple lookups from
  multi-step reasoning
- **Issue:** (none)
- **Status:** implemented

## Problem

The engine now has three answer paths — lexical retrieval (lookup), one-entity
cross-source composition, and multi-step reasoning — but the *user* must pick
the binary (`tessera` vs `tessera-compose`). Phase 2's roadmap requires the
system itself to distinguish a simple lookup from a question that needs
multi-step reasoning. This unit adds a deterministic, **explainable** router
(ADR 0006: rule-based, no LLM) and makes `uv run tessera` the single routed
door.

## Acceptance criteria (decided in autonomous mode)

- [ ] `routing.py`: `classify(question, graph) -> Route` with `kind` in
      `multi | entity | lookup` and a human-readable `reason` —
      routing decisions are themselves explainable, in the spirit of
      provenance. Rules: ≥2 named entities or a superlative phrasing → multi;
      exactly 1 named entity → entity composition; otherwise lookup
      (retrieval, which refuses on no relevant evidence).
- [ ] `route(question, graph, kb) -> tuple[Route, Answer]` dispatches to
      `reason` / `compose` / retrieval `answer`.
- [ ] `uv run tessera` routes automatically and **prints the route + reason**
      before the answer; `--engine` forces a specific path.
- [ ] The eval harness accepts `"engine": "route"` in gold cases (used by the
      synthetic generator, spec 0022).
- [ ] Existing gold cases (pinned engines) unchanged and green.

## Scope

**In:** router, routed CLI, harness `route` engine, tests. **Out:** LLM/NLU
(ADR 0006 triggers), conversational follow-ups, removing `tessera-compose`
(kept as a direct door).

## Eval impact

None on the numbers this unit (gold cases keep pinned engines). It makes the
router *evaluable* — synthetic routed cases in spec 0022 measure it.

## Risks

- Rule routing misses phrasings — surfaced as honest refusals downstream, and
  measurable via routed synthetic cases; ADR 0006 trigger 1 covers escalation.
