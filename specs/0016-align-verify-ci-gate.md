# 0016. One gate script shared by /verify and CI

- **Phase / milestone:** Phase 1 — interstitial hardening unit (between Unit 5 and Unit 6). Serves the "nothing unverified" guarantee in `CLAUDE.md` / `docs/ENGINEERING.md`.
- **Issue:** (none yet)
- **Status:** draft

## Problem

`/verify` checked formatting/linting by running the **pre-commit ruff hook**,
while CI runs `uv run ruff format --check .` and `uv run ruff check .` directly.
Those two invocations disagreed during Unit 1 (a "green" local `/verify` was
followed by a red CI), which quietly undermines the "nothing unverified" promise:
local green must mean CI green. The two check lists are maintained separately and
can drift. We want **one source of truth** the local gate and CI both run, before
the first real eval number lands in Unit 6.

## Acceptance criteria

- [ ] A committed **`scripts/gate.sh`** runs the canonical checks, in order:
      `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
      tests`, `uv run pytest`. Fails fast (`set -euo pipefail`); runnable from any
      directory (resolves repo root from its own path).
- [ ] **CI** (`.github/workflows/ci.yml`) runs the **same script** for those four
      checks (after `uv sync --frozen`, before the gitleaks secret scan) — no
      separately-maintained duplicate command list for format/lint/type/test.
- [ ] **`/verify`** (`.claude/commands/verify.md`) runs **`bash scripts/gate.sh`**
      for steps 1–4 (not the pre-commit ruff hook), then `uv run tessera-eval`
      (step 5) and the gitleaks secret scan — mirroring CI exactly.
- [ ] The `ruff` pin in `.pre-commit-config.yaml` is confirmed to match `uv.lock`
      (both `0.15.16`); the lockstep is documented so a future bump keeps them
      aligned.
- [ ] Running `bash scripts/gate.sh` locally is green on the current tree; CI stays
      green on the PR (proving local and CI now run identical checks).

## Scope

**In:** the shared `scripts/gate.sh`; pointing CI and `/verify` at it; confirming +
documenting the ruff pin lockstep; spec.

**Out:** changing *what* the checks are (same ruff/mypy/pytest config); the eval
harness and secret scan remain their own steps (run by each caller, as CI does);
auto-formatting behaviour at commit time (pre-commit still handles that on commit);
any new lint rules.

## Eval impact

None — this is gate tooling, not engine behaviour. It does not touch faithfulness/
coverage/quality (still 0 gold cases until Unit 6). Its value is making the gate
that *protects* those numbers trustworthy: local green == CI green.

## Risks / open questions

- **CI step granularity.** Folding four named steps into one `gate.sh` step means a
  failure shows as "gate" rather than the specific check; mitigated by the script
  echoing a header before each sub-check. Worth it for a single source of truth.
- **No ADR** — reversible tooling change.
