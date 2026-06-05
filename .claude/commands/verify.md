---
name: verify
description: Run the full quality gate — format, lint, type-check, tests, and the eval harness. Everything must be green before committing.
---

# /verify — The gate

Run the complete quality gate and report results clearly. This is the bar every change must clear before `/commit`.

Run, in order, and report pass/fail for each:
1. **Format check** — formatting is clean (ruff format / prettier).
2. **Lint** — no lint errors (ruff / eslint).
3. **Type-check** — no type errors (mypy/pyright; tsc strict).
4. **Unit tests** — all green (pytest / vitest).
5. **Eval harness** — run `uv run tessera-eval` and report the **faithfulness, coverage, and quality** numbers it prints, compared to the last recorded values in `docs/STATUS.md`. Until the curated gold set and metrics land (Unit 6), it honestly reports `no gold set evaluated yet` (0 gold cases) — that is a **pass**, not a failure; do not treat the absent number as red.

Rules:
- If anything fails, **stop and fix it before proceeding.** Do not commit on red.
- If an eval metric dropped, do not wave it through. Either fix the regression or, if the drop is genuinely justified, document the reason explicitly (it will go in the commit message and `STATUS.md`).
- Do not disable a check or weaken the eval to make the gate pass. That defeats the entire point of the project.

End with a one-line verdict: GREEN (safe to commit) or RED (with the blocking items listed).
