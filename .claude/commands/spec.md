---
name: spec
description: Write a specification for a unit of work into specs/ before any code is written. Use at the start of every feature, fix, or refactor.
---

# /spec — Specify before building

You are starting a new unit of work. **Do not write any implementation code in this step.** Produce a specification only.

Steps:
1. Read `CLAUDE.md`, the relevant docs in `docs/`, and `docs/STATUS.md` so the spec fits the project's principles and current state.
2. Confirm which roadmap phase and milestone this work belongs to (see `docs/ROADMAP.md`). If it doesn't fit the current phase, say so and stop — we don't build ahead of the plan.
3. Create a new file `specs/NNNN-short-slug.md` (next number in sequence) using `specs/TEMPLATE.md`, filling in:
   - **Problem** — what need this serves, in plain language.
   - **Acceptance criteria** — concrete, checkable conditions for "done."
   - **Scope: in / out** — explicitly list what this does NOT cover.
   - **Eval impact** — which faithfulness/coverage/quality metrics this should move, and in which direction. If "none," justify why.
   - **Risks / open questions.**
4. Keep it short — one page is the target. A spec that takes a day to write is a planning failure.
5. Do not proceed to implementation. End by summarizing the spec and asking for approval to move to `/plan`.

Guardrail: if the request is vague, ask the clarifying questions here, in the spec, rather than guessing in code later.
