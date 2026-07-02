# Specs

One spec per unit of work, written **before** any code, via the `/spec` command. A spec is the contract for a feature, fix, or refactor: it says what we're building, how we'll know it's done, and what it must not become. This is where scope creep is stopped.

- Numbered sequentially: `0001-short-slug.md`.
- Short — one page is the target.
- Each spec maps to a roadmap phase/milestone and (ideally) a GitHub issue.
- Use [`TEMPLATE.md`](TEMPLATE.md).

## Numbering ledger (gaps and irregularities)

Numbers get consumed in commit/PR references even when a session fails to commit
the spec file itself. The 2026-07-02 audit found seven such **phantom numbers**;
they are recorded here rather than backfilled with fabricated files (a spec
written after its code would not be a spec):

- **0050, 0069, 0071, 0076** — milestone-close/refactor units (M5 close, the
  stem-helper relocation, M8 close, M9 close) whose `docs/STATUS.md` entries
  served as the record.
- **0104, 0105, 0106** — Milestone 15 Units 2–3 and the recorder refactor
  (PRs #115–#117). The fullest record is ADR 0026 + the backfilled STATUS entry
  of 2026-07-01 + the PRs themselves.
- **0075 / 0079** share a basename slug across different milestones (M9/M10) —
  distinct specs, cosmetic collision.
- Spec 0103 internally reserved 0106/0107 for M15's send + close; those numbers
  were consumed otherwise. M15's remaining units execute under **spec 0111**,
  and Milestone 16 occupies **0107–0111** (spec 0107, decision 1).

The rule stands: the spec file lands in the unit's PR, **before** the code.
