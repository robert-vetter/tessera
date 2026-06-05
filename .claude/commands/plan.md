---
name: plan
description: Turn an approved spec into a reviewed implementation plan using plan mode. No code is written in this step.
---

# /plan — Plan before coding

An approved spec exists in `specs/`. Produce an implementation plan from it. **Write no code in this step.** Use plan mode.

Steps:
1. Read the relevant `specs/NNNN-*.md`, `CLAUDE.md`, and the design docs.
2. Lay out the plan:
   - The sequence of changes, smallest sensible increments first (vertical slice before breadth).
   - Which existing components are touched and how (at the level of responsibilities, not code).
   - What tests and eval cases will prove it works — name them before building them.
   - Whether any decision here is expensive to reverse; if so, flag that it will need an `/adr`.
3. Identify the riskiest assumption and how the plan de-risks it early.
4. Present the plan and **stop for review.** Do not implement until the plan is approved.

Principle: prefer a thin end-to-end path that can be demoed and measured over a broad, half-built layer. If the plan can't produce something runnable and measurable soon, simplify it.
