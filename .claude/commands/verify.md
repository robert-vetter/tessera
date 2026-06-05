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
5. **Eval harness** — run it and report the current **faithfulness, coverage, and quality** numbers, compared to the last recorded values in `docs/STATUS.md`.

Rules:
- If anything fails, **stop and fix it before proceeding.** Do not commit on red.
- If an eval metric dropped, do not wave it through. Either fix the regression or, if the drop is genuinely justified, document the reason explicitly (it will go in the commit message and `STATUS.md`).
- Do not disable a check or weaken the eval to make the gate pass. That defeats the entire point of the project.

End with a one-line verdict: GREEN (safe to commit) or RED (with the blocking items listed).
