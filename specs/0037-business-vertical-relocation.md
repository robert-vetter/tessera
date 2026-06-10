# 0037. The business answer layer moves beside tessera/devex/

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 3)
- **Issue:** —
- **Status:** approved (autonomous mode; executes the relocation ADR 0008 scheduled)

## Problem

ADR 0008 drew the core/vertical boundary and named an accepted asymmetry: the
DevEx vertical lives in `tessera/devex/`, while the business vertical's answer
layer (`composition`, `reasoning`, `conflicts`, `routing`'s business dispatch,
`knowledge`, `cli`, and the business synthetic generator hiding under the
generic name `eval/synthetic.py` — ADR 0009's accepted cost) still sits at the
engine's top level. The asymmetry was deliberate during the Phase 3 proof
(relocating mid-proof would have destroyed the "unchanged core" evidence);
Phase 4 is the scheduled time to repair it, so a stranger reading `src/tessera/`
sees the architecture ADR 0008 describes: a vertical-neutral core plus two
sibling verticals.

## Acceptance criteria

- [ ] `tessera/business/` exists with `cli`, `knowledge`, `composition`,
      `reasoning`, `conflicts`, `routing`, `synthetic` — moved with `git mv`
      (history preserved), contents unchanged except import paths and
      path-accurate docstring references.
- [ ] Core `tessera/routing.py` keeps **only** the vertical-neutral `Route`
      dataclass (the type both verticals' routers share); the business
      `classify`/`route` move to `tessera/business/routing.py`.
- [ ] The frozen-core list of ADR 0008 minus the relocated answer layer —
      `grounding`, `ingestion`, `graph`, `resolution`, `retrieval`,
      `sources/*` — is **diff-empty** in this PR.
- [ ] Entry points keep their names and behaviour: `uv run tessera`,
      `uv run tessera-compose` work exactly as before (targets repointed).
- [ ] All tests pass with imports updated; **both batteries' numbers are
      byte-identical** (7/52 and 7/24 cases, all 1.000) — verified by the
      pinned eval tests and a manual before/after run. No `--record` (nothing
      moved).
- [ ] `eval/metrics.py` changes in exactly one line: the `renewal_date_of`
      import path. The business claim-grammar leak it represents is Unit 4's
      job (ADR 0008 names it), not this unit's.

## Scope

**In:** the module moves, import updates (src/tests/pyproject), the `routing`
split, docs that name moved paths.

**Out:** any behaviour change; any signature change; the claim-grammar
relocation out of `eval/metrics.py` (Unit 4, ADR 0011); compatibility shims
(no external consumers exist — a clean move beats a deprecation layer);
moving `sources/salt.py`/`sources/documents.py` (sources already mirror
`sources/devex.py` — the per-vertical *sources* convention is one flat
`sources/` package, which both verticals share today).

## Eval impact

None — and that is the acceptance criterion: every recorded number reproduces
exactly through the move. Any drift is a regression to fix.

## Risks / open questions

- Hidden import-order or hash-seed sensitivity exposed by module renames —
  gate runs under multiple `PYTHONHASHSEED` values before merge.
- Docs referencing old paths (`src/tessera/composition.py`, etc.) go stale —
  swept here; the Unit 8 stranger pass re-checks.
