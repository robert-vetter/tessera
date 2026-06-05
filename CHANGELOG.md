# Changelog

All notable changes to Tessera are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are curated by hand from the project's [Conventional Commits](https://www.conventionalcommits.org/)
and rolled into a dated, versioned section at each roadmap-phase tag (the first
release, `v0.1.0`, is cut at the end of Phase 1).

## [Unreleased]

### Added

- **Python project (uv).** `pyproject.toml` managed by uv, with ruff
  (lint + format), mypy (strict), and pytest. Python pinned to 3.12 via
  `.python-version`, and `uv.lock` committed so the environment is reproducible
  from a clean clone.
- **Local quality gate (pre-commit).** Hooks for ruff lint/format, gitleaks
  secret scanning, and basic file hygiene, so commits are checked before they
  reach CI.
- **Continuous integration.** A GitHub Actions `gate` workflow that runs the
  same checks as the local gate — format, lint, type-check, tests, and a secret
  scan — on every pull request and push to `main`, against the locked
  environment.
- **Reproducible container.** A `Dockerfile` (pinned Python 3.12 + uv, non-root)
  and a VS Code devcontainer, so the project and its gate run identically
  anywhere with no host toolchain assumed.
- **Documentation site.** A MkDocs Material site built from `docs/` and deployed
  to GitHub Pages via GitHub Actions, with strict builds so broken links fail.
- **This changelog.**

[Unreleased]: https://github.com/robert-vetter/tessera/commits/main
