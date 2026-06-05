# 0003. CI workflow

- **Phase / milestone:** Phase 0 — Foundation and frame (remote quality gate)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ENGINEERING.md` §3 calls CI "the single most important 'this is serious'
signal": a green check on every PR, enforced remotely so nothing reaches `main`
unverified. Units 1–2 made the gate runnable locally; this unit mirrors it into
**GitHub Actions** so the same checks run on every pull request and push to
`main`, using the committed `uv.lock` so CI and a fresh clone resolve identical
dependencies. Once this exists and produces a named status check, branch
protection can require it — the manual step `docs/SETUP.md` Stage A3 describes.

## Acceptance criteria

- [ ] `.github/workflows/ci.yml` exists, triggering on `pull_request` and on
      `push` to `main`.
- [ ] Sets up uv (pinned action) and the project Python (3.12, from
      `.python-version`), then `uv sync --frozen` so a drifted lockfile fails CI.
- [ ] Runs the same four gates as `/verify`, each a visible step:
      `ruff format --check .`, `ruff check .`, `mypy src tests`, `pytest`.
- [ ] Also runs a **gitleaks** secret scan as a CI step (defense in depth, in
      case a contributor skipped `pre-commit install`).
- [ ] Exposes a single, stable status-check name branch protection can require.
- [ ] Uses least-privilege `permissions` (read-only contents) and a
      `concurrency` group that cancels superseded runs on the same ref.
- [ ] The workflow is valid YAML and passes the repo's `check-yaml` pre-commit
      hook; the four commands it runs are confirmed green locally first.

## Scope

**In:** one CI workflow running the four existing quality gates via uv against
the locked environment, with sensible triggers, permissions, and concurrency.

**Out:** the **eval regression** step (added in Phase 1 when the harness
exists), the **docs build/deploy** step (unit 5, MkDocs), coverage upload and
badges (unit 8 / Phase 1), frontend/TypeScript CI (deferred), release/changelog
automation, and **enabling branch protection itself** — that is a manual repo
setting you perform after this lands (`docs/SETUP.md` A3), not something this
unit can or should do.

## Eval impact

None directly. The eval harness does not exist yet, so CI cannot run it; the
workflow is structured so the eval step slots in cleanly in Phase 1. This unit
protects the metric *indirectly* by guaranteeing the gate runs on every change.

## Risks / open questions

- **Can't observe true green without GitHub.** A workflow's real pass/fail only
  shows on the runner. De-risk: run the four commands locally (already green),
  validate the YAML, and treat the first PR as the live confirmation per
  `docs/SETUP.md` B3. Low-risk — the steps are identical to the local gate.
- **Secret scan in CI** — **confirmed yes**: CI also runs gitleaks, so secrets
  are caught even if a contributor skipped `pre-commit install`. Cheap step,
  **no ADR**.
- **Lockfile strictness.** Using `uv sync --frozen` makes a stale `uv.lock` a CI
  failure — intended (reproducibility), noted so it is not a surprise.
