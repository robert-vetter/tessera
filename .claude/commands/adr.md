---
name: adr
description: Record an architecture decision in docs/adr/ when a choice is expensive to reverse. Use for storage choices, grounding approach, eval definitions, and similar.
---

# /adr — Record a decision

Use when a decision is expensive to reverse and a future reader will ask "why was it done this way?"

Steps:
1. Read `docs/adr/README.md` and the existing ADRs so the new one is consistent and correctly numbered.
2. Create `docs/adr/NNNN-short-title.md` from `docs/adr/0000-template.md`, filling in:
   - **Status** — proposed / accepted / superseded.
   - **Context** — the forces at play, honestly (constraints, trade-offs, what we don't know).
   - **Decision** — what was chosen.
   - **Consequences** — what becomes easier, what becomes harder, what we accept.
   - **Alternatives considered** — and why they lost. This section is what signals real engineering judgment.
3. If this ADR supersedes an earlier one, mark the old one `superseded by NNNN` — never delete it.
4. Keep it short and concrete. An ADR is a record, not an essay.
