# 0011. Evaluation harness scaffold

- **Phase / milestone:** Phase 1 — The thin vertical slice. Unit 1b (between Unit 1 and Unit 2). Serves the standing principle "keep the eval runnable at all times"; the real gold set + faithfulness number is Unit 6.
- **Issue:** (none yet)
- **Status:** draft

## Problem

"Trust is measured" is a non-negotiable principle, and the engineering rule is to
"keep the eval green and meaningful" from the start. Today there is no eval to
run at all — `/verify` step 5 has nothing to invoke, and `docs/STATUS.md` records
no number. This unit puts the **plumbing** in place so every later unit runs the
eval as part of the gate, *before* any metric is computed. The point is honesty:
with no gold set yet, the harness must say so plainly ("no gold set evaluated
yet") rather than print a fabricated or decorative number. The real metric
definitions and gold cases are deliberately deferred to Unit 6 (where the
faithfulness definition is itself ADR-worthy).

## Acceptance criteria

- [ ] A runnable entry point — `uv run tessera-eval` — loads the gold set and
      prints an honest report. With **zero** gold cases it states **"no gold set
      evaluated yet"** and reports faithfulness / coverage / quality as
      **n/a (0 gold cases)**. Exit code 0.
- [ ] The harness is **importable**: `run_eval(...)` returns a typed `EvalReport`
      with `gold_case_count: int` and `faithfulness | coverage | quality:
      float | None` (None until Unit 6 computes them). No fabricated numbers.
- [ ] The three metric **names** are fixed (faithfulness, coverage, quality) but
      their **computation is explicitly deferred** to Unit 6 — the scaffold loads
      cases and counts; it does not score.
- [ ] A **test** exercises the harness so it cannot silently bitrot: `run_eval()`
      returns count 0 and `None` metrics, and the rendered summary contains "no
      gold set evaluated yet". (This keeps CI exercising the eval via pytest.)
- [ ] `README` documents `uv run tessera-eval`; `/verify` step 5 now has a real
      command to run.
- [ ] Gate green, verified with the **CI-equivalent** commands
      (`uv run ruff format --check .`, `uv run ruff check .`, mypy, pytest), not
      only the pre-commit hook.

## Scope

**In:** a small `tessera.eval` package (harness + typed `EvalReport` + a gold-set
loader that returns `[]` when none exist); a `tessera-eval` CLI entry point; a
minimal `GoldCase` shape; one test; README + run docs.

**Out:** the actual **metric computation and definitions** (Unit 6 — and the
faithfulness definition's ADR); the **gold cases** themselves; **synthetic data
generation** (Phase 2); LLM-judged faithfulness; **regression history / tracking
over time**; comparison against last-recorded numbers; adding a separate eval
**CI job** (the pytest test already exercises the harness in CI). The `GoldCase`
shape is kept intentionally minimal so it does not pre-empt Unit 6's metric
design.

## Eval impact

Establishes the harness; there is still **no faithfulness number** (0 gold cases),
and the report says so. This is the honest seed of the metric, not the metric.
`docs/STATUS.md` will record "harness runnable; 0 gold cases; metrics n/a."

## Risks / open questions

- **No hard-to-reverse decision here → no ADR.** The metric *definition* in Unit 6
  is the ADR-worthy choice; this unit deliberately avoids fixing it.
- **Over-design risk:** baking expected-answer fields or scoring into `GoldCase`
  now would front-run Unit 6. Mitigated by keeping `GoldCase` minimal and stating
  the deferral in code.
