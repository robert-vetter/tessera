# 0001. Record architecture decisions

- **Status:** accepted
- **Date:** (set on creation)

## Context
This is a multi-month project built largely through an AI coding agent across many sessions. Decisions made early will be invisible later unless they are written down, and "why is it like this?" is the question that most often derails long solo projects.

## Decision
We will keep Architecture Decision Records in `docs/adr/`, one per non-trivial, hard-to-reverse decision, created via the `/adr` command and following the template. Records are append-only; superseded ones are marked, not deleted.

## Consequences
- Easier: any reviewer (or future self, or a fresh agent session) can reconstruct the reasoning behind the system.
- Easier: it forces alternatives to be considered explicitly before committing to a path.
- Harder: a small, ongoing discipline cost — a few minutes per significant decision.
- Accepted: that cost is trivial next to the cost of an undocumented decision discovered three months in.

## Alternatives considered
- **No formal record (rely on commit messages).** Rejected: commit messages capture *what* changed, not the weighing of options behind a structural choice, and they are hard to navigate as a decision log.
- **A single running decisions document.** Rejected: it grows unwieldy, merges poorly, and loses the one-decision-per-record clarity that makes ADRs easy to reference and supersede.
