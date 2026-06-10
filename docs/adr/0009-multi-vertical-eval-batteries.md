# 0009. The eval harness measures verticals as batteries

- **Status:** accepted
- **Date:** 2026-06-10

## Context

Trust is measured (principle 3), and Phase 3's milestone is two verticals
*both measured*. The Phase 2 harness is hardwired to one vertical: it builds
`build_demo_graph()`/`DEMO_KB`, dispatches `case.engine` to the business
answer paths, generates one synthetic battery, and records a
`{gold, synthetic}` pair to `eval/history.jsonl` and one badge. Every one of
those bindings must become per-vertical without vertical-specific logic
entering the scoring internals (ADR 0008), and without invalidating the
existing append-only history.

## Decision

**A `Battery` is the unit of measurement.** A frozen dataclass
(`tessera/eval/battery.py`) bundling what the harness needs to measure one
vertical: `name`, `gold_dir`, `build_graph()`, `build_kb()`,
`answer(case, graph, kb)` (the vertical's engine dispatch), and
`synthetic(graph, kb)` (its generator). Scoring (`_score`) stays a single,
shared, vertical-neutral function; faithfulness/coverage/quality definitions
do not change.

**Wiring lives in one named place.** `tessera/eval/registry.py` is the *only*
eval module that imports vertical code; it returns the tuple of batteries
(business, devex). Like `cli.py`, it is wiring, not internals — the scoring
machinery never branches on a vertical.

**Gold sets move under per-battery directories:** `eval/gold/business/`
(the existing 7 cases, unmodified) and `eval/gold/devex/`.

**The floor gates everything.** `tessera-eval` exits non-zero if *any*
battery's gold or synthetic faithfulness is < 1.0. Coverage and quality stay
reported-not-gated, per battery.

**History schema v2, append-only.** New lines are
`{"recorded", "note", "batteries": [{"name", "gold": {...}, "synthetic": {...}}]}`.
Existing v1 lines are never rewritten (the journal is history); readers keep
returning raw dicts, so both shapes coexist.

**The badge stays one number, now meaning more:** the **minimum** gold
faithfulness across batteries, green only while the floor holds everywhere.
A regression in *either* vertical turns the README red.

## Consequences

- Adding vertical N+1 to the eval = one `Battery` value + a gold directory;
  scoring code untouched.
- The business battery must reproduce its Phase 2 numbers exactly through the
  refactor — that equality is itself a regression test, run before any DevEx
  battery exists (spec 0032).
- Accepted cost: history consumers must handle two line shapes. Chosen over
  migrating the journal (append-only means *append-only*) and over a separate
  v2 file (splits the trend story).
- Accepted cost: `eval/synthetic.py` (the business generator) keeps its
  misleadingly generic name until the Phase 4 relocation (ADR 0008).

## Alternatives considered

- **A second, parallel harness for DevEx.** Rejected: forks the metric
  definitions — the moment they drift, "faithfulness" stops meaning one
  thing, which is the project's central number (ADR 0005).
- **One merged battery (run both verticals' cases through one graph/KB).**
  Rejected: cross-vertical contamination (a business question retrieving log
  lines is noise, not generality) and the per-vertical numbers — the thing
  the milestone asks for — disappear into an average.
- **Entry-point/plugin discovery of batteries.** Rejected: dynamic discovery
  for exactly two known verticals adds indirection and a failure mode
  (silently missing battery = silently unmeasured vertical) where an explicit
  tuple keeps the measured set visible in one line of code.
- **Badge per battery.** Rejected for now: two badges say less than one
  honest minimum; per-battery numbers live in the history journal and the
  CLI output.
