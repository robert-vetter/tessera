# 0001. Python project config

- **Phase / milestone:** Phase 0 — Foundation and frame (reproducible local environment)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

Tessera has design docs but no code and no toolchain. Phase 0 requires a
*reproducible local environment so anyone can run what exists*, and every later
unit (pre-commit, CI, Docker) depends on a Python project being defined first.
This unit lays that foundation: a `pyproject.toml` managed by **uv** with
**ruff** (lint + format), **mypy** (strict), and **pytest**, a pinned Python
version, a committed lockfile, and a minimal package plus one passing test — so
the `/verify` gate can run GREEN on a near-empty project before any feature
exists. Per `docs/SETUP.md` Stage B3, a green gate on near-zero code is the
proof the machinery is real.

## Acceptance criteria

- [ ] `pyproject.toml` exists with project metadata, `requires-python`, and
      configured `ruff`, `mypy` (strict), and `pytest` sections.
- [ ] Python version is pinned in `.python-version`, consistent with
      `requires-python`.
- [ ] `uv.lock` is generated and committed (env is reproducible from clone).
- [ ] A minimal `src/tessera/` package exists (importable, with `__init__.py`
      exposing a version).
- [ ] At least one trivial test under `tests/` passes via `uv run pytest`.
- [ ] All four gate steps pass on the new code:
      `ruff format --check .`, `ruff check .`, `mypy`, `pytest`.
- [ ] A reader can clone, run `uv sync`, and execute the test suite using only
      the README/spec instructions.

## Scope

**In:** Python packaging/tooling config (`pyproject.toml`, `.python-version`,
`uv.lock`), the minimal `src/tessera/` package, one trivial test, and the tool
configs (ruff/mypy/pytest) needed for `/verify`'s first four steps to pass.

**Out:** Pre-commit hooks (unit 2), CI (unit 3), Docker/devcontainer (unit 4),
docs site (unit 5), frontend/pnpm config (deferred until the conversational
surface), the eval harness (Phase 1), and any application logic. No real
Tessera features — only the skeleton.

## Eval impact

None. The eval harness does not exist until Phase 1, so `/verify`'s eval step
is legitimately N/A and will report "no eval yet" rather than a fabricated
number. This unit moves no faithfulness/coverage/quality metric; it exists to
make those metrics *runnable later* by establishing the test/tooling substrate.

## Risks / open questions

- **Python version choice** — **confirmed 3.12** (current, widely-available
  stable; broad wheel support; safest for later SAP AI Core / HANA client
  libraries). `requires-python = ">=3.12"`, `.python-version` = `3.12`.
- **src layout vs flat** — proposing `src/` layout (standard, avoids import
  ambiguity). Low-risk, conventional; not ADR-worthy.
- **Lockfile in VCS** — committing `uv.lock` is the reproducibility requirement;
  no open question, just noted for the reviewer.
- No decision here is hard to reverse, so **no ADR** is expected for this unit.
