# 0059. Close Milestone 6 — the docs, the tag, the trail

- **Phase / milestone:** Milestone 6 — Embeddings on SAP (Unit 9 of 9; plan 0051)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The work is done and recorded; this unit makes the milestone *legible to a
stranger*: the WRITEUP tells the embeddings-on-SAP story honestly (including the
long-log dilution and the not-CI-reproducible caveat), the README's eval block
matches reality (offline 0.833 + the SAP close explained), the CHANGELOG and
STATUS reflect it, the gate is green under multiple hash seeds, and the milestone
is tagged.

## Acceptance criteria

- [x] Gate green under multiple `PYTHONHASHSEED` values (0/1/42/2026): 263 tests,
      `github_actions` gold stable at 0.833 offline.
- [x] `docs/WRITEUP.md`: a "Milestone 6: embeddings on SAP" section; the
      limitations + deferred-work sections updated (retrieval-only, cloud-measured,
      long-log dilution); the "why not embeddings (yet)" forward-pointer.
- [x] `README.md`: the eval block shows the real offline `github_actions` gold
      0.833, with the SAP online close explained and linked.
- [x] `CHANGELOG.md` `[milestone-6]`; `docs/STATUS.md` entry.
- [ ] Tag `milestone-6`; memory updated; next-milestone kickoff handed back.

## Scope

**In:** WRITEUP/README/CHANGELOG/STATUS updates; this spec; the tag; the memory
update.

**Out:** any code or eval change (the numbers are frozen by U8). No new claims —
only the honest record of what was built and measured.

## Eval impact

None — documentation. The frozen numbers: business/devex all 1.000;
`github_actions` gold faithfulness 1.000, coverage 0.833 offline / 1.000 online
(recorded), quality 0.800 / 1.000.

## Risks / open questions

- The README/WRITEUP must not overclaim "ran on SAP" beyond what the recorded
  point supports: it is one timestamped online run, not a CI gate. Stated as such
  everywhere it appears.
