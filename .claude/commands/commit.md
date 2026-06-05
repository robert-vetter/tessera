---
name: commit
description: Stage a single logical change and write a Conventional Commit message explaining what changed and why. Only run after /verify is green.
---

# /commit — Small, honest commits

Precondition: `/verify` is GREEN. If it is not, stop and run `/verify` first.

Steps:
1. Review the working changes. If they contain **more than one logical change**, split them — one commit per logical change. Resist the urge to bundle.
2. Stage the files for this one change.
3. Write a **Conventional Commit**:
   - Type: one of `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `eval`.
   - Scope: the area touched (e.g. `ingestion`, `graph`, `eval`, `devex`).
   - Subject: imperative, concise.
   - Body: explain **why**, not just what. If an eval metric moved, state the before/after and the reason.
   - Footer: reference the spec (`Spec: specs/NNNN-…`) and any issue.
4. Keep commits frequent and small — the history is part of the deliverable and should read as steady, thoughtful progress.

Guardrail: never commit secrets, credentials, or large data artifacts. If the secret-scanner flags something, stop.
