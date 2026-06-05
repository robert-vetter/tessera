# 0004. Dockerfile + devcontainer

- **Phase / milestone:** Phase 0 — Foundation and frame (reproducibility)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ENGINEERING.md` §3 requires that "anyone (including a reviewer) can clone
and run the current state with one command" — "it works on my machine" is not a
defense. Units 1–3 made the environment reproducible *if you already have uv*;
this unit removes that precondition. A `Dockerfile` and a VS Code **devcontainer**
give a clean, pinned environment (Python 3.12 + uv, deps from the committed
`uv.lock`) so the project builds and its gate runs identically anywhere — on a
reviewer's laptop or in Codespaces — with no host toolchain assumed.

## Acceptance criteria

- [ ] A `Dockerfile` at the repo root, based on a **pinned** Python 3.12 + uv
      image, that installs dependencies from `uv.lock` with `uv sync --frozen`
      and runs as a **non-root** user.
- [ ] `docker build` succeeds locally.
- [ ] The full gate runs **green inside the container** — `ruff format --check .`,
      `ruff check .`, `mypy src tests`, `pytest` — proving the container
      reproduces the local environment, not just builds.
- [ ] A `.dockerignore` keeps the build context small (excludes `.venv`, `.git`,
      `__pycache__`, caches, etc.).
- [ ] `.devcontainer/devcontainer.json` is valid JSON, builds from the
      `Dockerfile`, lands in the right workspace folder, ensures the env on
      create (`uv sync`), and pre-installs the relevant editor tooling (Python +
      ruff).
- [ ] README documents the one-command build/run path.

## Scope

**In:** `Dockerfile`, `.dockerignore`, `.devcontainer/devcontainer.json`, and a
short README note. The image is for **development/reproducibility** — a clean
place to build and run the gate.

**Out:** publishing the image to a registry; multi-arch / production-hardened or
minimized runtime images; building the image **in CI** on every PR (a possible
later hardening, kept out to keep CI fast — verified locally instead); any
frontend/Node container (deferred with the conversational surface); and the
"hello world" app itself (unit 9).

## Eval impact

None. Reproducibility tooling; it touches no faithfulness/coverage/quality
metric (the eval harness arrives in Phase 1). It does make the *future* eval
trivially reproducible for a reviewer, which is the indirect point.

## Risks / open questions

- **Base image choice** — **confirmed** `ghcr.io/astral-sh/uv:python3.12-*-slim`
  (uv + Python 3.12 pre-pinned, minimal, Astral-maintained). Low-risk, easily
  swapped — **no ADR**.
- **CI image build** — **confirmed out of scope**: the build/gate is verified
  locally; CI stays fast. A CI image-build job remains a clean later hardening.
- **Local-only build proof.** Docker is available locally, so the build/gate is
  verified here. Without a CI image-build job (out of scope), the container is
  not re-verified on every PR; acceptable for Phase 0 and noted honestly.
- **devcontainer drift.** The devcontainer must build from the same `Dockerfile`
  (not a divergent inline image) so there is one definition to maintain.
