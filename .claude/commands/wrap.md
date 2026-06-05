---
name: wrap
description: End the work session cleanly by updating docs/STATUS.md with what was done, what's next, and open questions. Run before stopping work.
---

# /wrap — Close the session

The single most important anti-drift habit. Before stopping, capture the state so the next session (yours or a fresh Claude session) starts from writing, not memory.

Update `docs/STATUS.md` with a new dated entry containing:
1. **Done this session** — what was completed and committed (reference commits/specs).
2. **Current eval numbers** — latest faithfulness / coverage / quality, so the trend is tracked in one place.
3. **Next** — the immediate next unit of work, specific enough to start cold.
4. **Open questions / risks** — anything unresolved, any decision pending an `/adr`.
5. **State of the tree** — is `main` green? Any branch left open?

Keep older entries; `STATUS.md` is append-only history. End by confirming the file is updated and the tree is in a known state (no uncommitted surprises).
