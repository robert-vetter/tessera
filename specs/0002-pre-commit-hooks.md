# 0002. Pre-commit hooks

- **Phase / milestone:** Phase 0 — Foundation and frame (local quality gate)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`main` must be protected by default, not by willpower. `docs/ENGINEERING.md` §3
calls for a **pre-commit framework** that runs formatters, linters, and a
**secret-scanner** before any commit reaches CI, so a mistake is caught at the
cheapest possible moment. Unit 1 gave us ruff configured in `pyproject.toml`;
this unit wires those checks (plus basic file hygiene and secret scanning) into
git via `.pre-commit-config.yaml`, reusing the single source of truth rather
than duplicating rules. It is the local half of the "nothing unverified"
guarantee; CI (unit 3) is the remote half.

## Acceptance criteria

- [ ] `.pre-commit-config.yaml` exists with **pinned** hook revisions for
      reproducibility.
- [ ] Hooks included: **ruff lint** (with `--fix`) and **ruff format** (from the
      official `ruff-pre-commit`, version aligned with the locked ruff), a
      **secret-scanner**, and basic hygiene hooks (trailing whitespace,
      end-of-file fixer, `check-yaml`, `check-toml`,
      `check-added-large-files`, `check-merge-conflict`).
- [ ] Hooks do **not** conflict with `pyproject.toml`'s ruff config (no
      back-and-forth reformatting; same line-length and rule set).
- [ ] `pre-commit run --all-files` exits **0** on the current tree.
- [ ] The secret-scanner produces no false positives on the current tree (a
      committed baseline/allowlist is acceptable if its contents are explained).
- [ ] README/SETUP note records the one manual step: `pre-commit install`.

## Scope

**In:** `.pre-commit-config.yaml` (ruff lint+format, secret-scanner, hygiene
hooks), any minimal config the secret-scanner needs (e.g. a baseline), and a
short doc note that `pre-commit install` is run once locally.

**Out:** Running `mypy` or `pytest` as pre-commit hooks — those stay in
`/verify` and CI (unit 3), where slower checks belong; pre-commit is for fast,
every-commit gates. Also out: CI itself, Docker, docs site, frontend hooks, and
actually executing `pre-commit install` for the user (it modifies their local
git config — a manual step per `docs/SETUP.md`).

## Eval impact

None. This is tooling that protects the repository; it touches no
faithfulness/coverage/quality metric (the eval harness arrives in Phase 1).

## Risks / open questions

- **Secret-scanner choice** — **confirmed gitleaks** (self-contained binary
  managed by pre-commit, no baseline file to maintain — lower ceremony than
  `detect-secrets`). Low-risk, easily swapped — **no ADR**.
- **First-run network** — pre-commit downloads/builds hook environments on
  first run; CI and contributors need network once to populate the cache. Noted,
  not blocking.
- **Should `pre-commit install` be automated?** No — it writes to the user's
  local `.git/hooks`; kept manual and documented per Setup Stage A/B.
