---
name: audit
description: Weekly health check. Scan the repository for drift — stale docs, untested code, scope creep, broken invariants — and report findings without fixing them yet.
---

# /audit — Drift check

Run roughly weekly. The goal is to **detect** drift, not silently fix it — produce a report, then decide what to act on.

Check and report on:
1. **Docs vs. reality** — do `PROJECT_BRIEF`, `CAPABILITIES`, `ROADMAP`, and `ENGINEERING` still describe what the code actually does? List any mismatch.
2. **Specs** — are there `specs/` entries with no corresponding implementation, or code with no spec? Flag both.
3. **Eval health** — is the harness still meaningful? Are there capabilities with no eval coverage? Is the faithfulness trend going the right way?
4. **Test coverage** — modules with little or no test coverage.
5. **Scope** — has anything crept in that isn't in the current roadmap phase? Name it.
6. **Decisions** — were any non-trivial choices made recently without an ADR?
7. **Tree hygiene** — stale branches, uncommitted state, failing CI on `main`.

Output a prioritized findings list (high / medium / low). Do not make changes in this command — propose follow-up `/spec`s or fixes for the items worth acting on, and record anything systemic in `docs/STATUS.md`.
