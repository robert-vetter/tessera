# 0007. Issue/PR templates + Dependabot

- **Phase / milestone:** Phase 0 — Foundation and frame (housekeeping)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ENGINEERING.md` §3 asks for **issue/PR templates** "so even solo work is
filed consistently," and the project pins all dependencies and GitHub Actions by
exact version/SHA for reproducibility — which only stays current if something
proposes updates. This unit adds the GitHub `.github` housekeeping that makes
contributions consistent and keeps the pins fresh: issue templates, a pull-request
template that mirrors the project's spec/verify discipline, and a **Dependabot**
config covering every ecosystem in use. Dependabot's `github-actions` updates
also resolve the standing Node-20 action-deprecation warning by bumping the
SHA-pinned actions to current versions.

## Acceptance criteria

- [ ] A **pull-request template** (`.github/PULL_REQUEST_TEMPLATE.md`) reflecting
      the loop: linked spec, summary, verification (gate green), scope/deferrals,
      eval impact.
- [ ] **Issue templates** under `.github/ISSUE_TEMPLATE/` for at least a bug
      report and a feature/unit-of-work request, plus `config.yml` (e.g.
      `blank_issues_enabled`) as appropriate.
- [ ] A **`.github/dependabot.yml`** with update schedules for every ecosystem
      present: **`github-actions`**, **`uv`** (Python), and **`docker`** (the
      base image), each grouped/scheduled sensibly with Conventional-Commit
      commit messages.
- [ ] All new files are valid (YAML parses; pre-commit `check-yaml` passes) and
      the existing `gate` check and host `/verify` remain green.
- [ ] No change to application code, CI logic, or the docs build.

## Scope

**In:** `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/*`
(+ `config.yml`), and `.github/dependabot.yml` covering github-actions, uv, and
docker, with Conventional-Commit messages and a sane cadence.

**Out:** CODEOWNERS, contributing guide / code of conduct, GitHub Projects or
labels automation, auto-merge for Dependabot PRs, security policy
(`SECURITY.md`), and the README **badges** (unit 8). Actually *enabling*
Dependabot is automatic for the committed config — no manual repo toggle needed
beyond what a public repo provides by default.

## Eval impact

None. Repository housekeeping; it touches no faithfulness/coverage/quality
metric (the eval harness arrives in Phase 1).

## Risks / open questions

- **Issue template format** — **confirmed YAML issue forms** (structured fields,
  required inputs; guides filers and reads as a well-run repo). Cheap to
  reverse — **no ADR**.
- **Dependabot cadence** — **confirmed weekly, grouped** (minor/patch grouped
  into one PR per ecosystem) to keep pins fresh without flooding PRs.
- **Dependabot `uv` support.** Dependabot supports the `uv` package ecosystem;
  confirm the exact ecosystem key during `/plan` so it actually tracks
  `pyproject.toml`/`uv.lock` (incl. dev and docs groups).
- **PR noise / cadence.** A weekly schedule with grouped updates keeps
  Dependabot from flooding PRs; noted so the cadence is deliberate.
- **Templates won't break CI.** They are inert Markdown/YAML; the only
  verification is validity + that nothing else regresses.
