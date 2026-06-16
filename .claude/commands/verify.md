---
name: verify
description: Run the full quality gate — format, lint, type-check, tests, and the eval harness. Everything must be green before committing.
---

# /verify — The gate

Run the complete quality gate and report results clearly. This is the bar every change must clear before `/commit`.

Run, in order, and report pass/fail for each:
1. **Gate script** — run `bash scripts/gate.sh`. This is the **single source of truth** the CI `gate` job also runs, so a green local gate means a green CI gate. It runs, in order, and you should report pass/fail for each: `ruff format --check .` (format), `ruff check .` (lint), `mypy src tests` (type-check), `pytest` (tests), and `tessera-eval` (the **faithfulness floor** — non-zero exit if any battery's faithfulness < 1.0). Do **not** substitute the pre-commit ruff hook — it has diverged from these commands before.
2. **Eval numbers** — `tessera-eval` already ran inside the gate (step 1) and gated the floor; here, read its output and report the **faithfulness, coverage, and quality** numbers compared to the last recorded values in `docs/STATUS.md` / `eval/history.jsonl`. The floor (faithfulness) is hard-gated; coverage/quality are reported, improvable targets — a deliberate, documented coverage/quality drop is not red, but an *unexplained* one is.
3. **Secret scan** — run `uv run pre-commit run gitleaks --all-files` (the same scan CI runs).

Rules:
- If anything fails, **stop and fix it before proceeding.** Do not commit on red.
- If an eval metric dropped, do not wave it through. Either fix the regression or, if the drop is genuinely justified, document the reason explicitly (it will go in the commit message and `STATUS.md`).
- Do not disable a check or weaken the eval to make the gate pass. That defeats the entire point of the project.

End with a one-line verdict: GREEN (safe to commit) or RED (with the blocking items listed).
