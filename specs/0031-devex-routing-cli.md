# 0031. DevEx routing + the `tessera-devex` door

- **Phase / milestone:** Phase 3 — second vertical (DevEx Copilot), Unit 6
- **Issue:** —
- **Status:** approved (autonomous mode; decisions recorded here)

## Problem

The DevEx vertical needs one routed conversational door, like
`uv run tessera` is for the business vertical: a question goes in, the
router says *where it sent it and why*, and the answer (or principled
refusal) comes back. Question shapes are inherently per-vertical (ADR
0008), so the dispatch lives in the vertical; the core `routing.py` stays
frozen. What *is* shared: the `Route` value (imported, not copied), the
refuse-on-fallthrough discipline, and the core BM25 retrieval as the
lookup path over the DevEx KB.

## Acceptance criteria

- [ ] `tessera/devex/routing.py`: `classify()` + `route()` — a named run →
      `rca`, a named PR → `summary` (run wins if both, recorded rule),
      otherwise `lookup` via the engine's unchanged lexical retrieval over
      the DevEx KB (which refuses on zero overlap). Every decision carries
      a reason.
- [ ] `tessera/devex/cli.py` + `tessera-devex` script entry: prints
      `[route: …]` then the rendered answer; `--engine` forces a path;
      default question is the flagship RCA demo.
- [ ] End-of-session demo: `uv run tessera-devex` answers "Why did run
      R-1042 fail?" with provenance on every claim; an out-of-corpus
      question refuses.
- [ ] Zero core changes (pyproject script entries are packaging, not core).

## Scope

**In:** vertical routing, CLI, tests.
**Out:** component/on-call entity questions as a routed class (the lookup
path serves them as far as lexical retrieval can — its measured limits are
exactly what Unit 8's gold set should capture); cross-vertical routing (one
door across both verticals is Phase 4 surface work).

## Eval impact

None yet; Unit 8's battery uses `route` as its dispatch. Business numbers
unchanged.

## Risks / open questions

- Run/PR id regexes are the corpus's shapes (`R-\d+`, `PR-\d+`); real CI
  systems differ — connector-level concern, out of scope (spec 0025).
