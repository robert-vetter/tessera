---
name: verify
description: Run the full quality gate — format, lint, type-check, tests, and the eval harness. Everything must be green before committing.
---

# /verify — The gate

Run the complete quality gate and report results clearly. This is the bar every change must clear before `/commit`.

Run, in order, and report pass/fail for each:
1. **Gate script** — run `bash scripts/gate.sh`. This is the **single source of truth** the CI `gate` job also runs, so a green local gate means a green CI gate. It runs, in order, and you should report pass/fail for each: `ruff format --check .` (format), `ruff check .` (lint), `mypy src tests` (type-check), `pytest` (tests). Do **not** substitute the pre-commit ruff hook — it has diverged from these commands before.
2. **Eval harness** — run `uv run tessera-eval` and report the **faithfulness, coverage, and quality** numbers it prints, compared to the last recorded values in `docs/STATUS.md`. Until the curated gold set and metrics land (Unit 6), it honestly reports `no gold set evaluated yet` (0 gold cases) — that is a **pass**, not a failure; do not treat the absent number as red.
3. **Secret scan** — run `uv run pre-commit run gitleaks --all-files` (the same scan CI runs).

Rules:
- If anything fails, **stop and fix it before proceeding.** Do not commit on red.
- If an eval metric dropped, do not wave it through. Either fix the regression or, if the drop is genuinely justified, document the reason explicitly (it will go in the commit message and `STATUS.md`).
- Do not disable a check or weaken the eval to make the gate pass. That defeats the entire point of the project.

End with a one-line verdict: GREEN (safe to commit) or RED (with the blocking items listed).
