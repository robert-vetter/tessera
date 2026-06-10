# 0036. Declared catalog aliases close the measured devex coverage gap

- **Phase / milestone:** Phase 4 — platform, polish, and the story (spec 0035 Unit 2)
- **Issue:** —
- **Status:** approved (autonomous mode; ADR 0010 records the direction decision)

## Problem

The devex gold coverage is **0.917** — the *named* `notif-svc` miss planted in
spec 0026 and predicted in spec 0033: the on-call export says `notif-svc`, the
catalog says `notifications-service`, similarity 0.429 is far below the 0.85
threshold, so the on-call row never joins the component's entity and the
on-call answer cannot surface it. This fired the ADR 0003/0004 revisit
triggers with a real measurement. The first trust loop closes it the way a
real organization would: **someone declares the alias in the service catalog**
— deterministic, additive data — before reaching for embeddings (ADR 0010
records the reassessment).

## Acceptance criteria

- [ ] `components.csv` carries an `Aliases` column; `SVC-NOTIF` declares
      `notif-svc`. The generator produces it; committed corpus == regeneration.
- [ ] `DevExSource` exposes `declared_aliases()`; the component record's text
      states the alias (the declaration is itself citable evidence).
- [ ] `build_devex_graph()` asserts a `Resolution` for each declared alias that
      exactly names an existing name-bearing node (confidence 1.0, reason
      naming the declaration) — additive and reversible like every resolution.
- [ ] A new devex **service route**: a question naming a catalog service (by
      name or declared alias) is answered from the resolved entity's records
      (catalog row + on-call rows), every claim a verbatim cited snippet; an
      ambiguous service reference refuses. RCA/summary routes keep precedence.
- [ ] Gold case 04 (`notifications-service` on-call) now also expects the
      answer to *contain* "Aiko Tanaka"; **devex gold coverage 0.917 → 1.000**,
      everything else pinned unchanged; recorded with `tessera-eval --record`.
- [ ] `checkout-svc` (0.846) stays **undeclared and unresolved** — the retained
      named near-miss proving aliases only fix what someone declares.
- [ ] ADR 0010 records: aliases first; embeddings (ADR 0003/0004 triggers)
      reassessed against the post-fix numbers and deferred again with a
      refreshed trigger; addenda on ADR 0003/0004 point here.

## Scope

**In:** generator + corpus, `sources/devex.py`, `tessera/devex/knowledge.py`,
new `tessera/devex/ownership.py`, `tessera/devex/routing.py`, `tessera/devex/cli.py`
(`--engine service`), gold case 04, tests, ADR 0010 + addenda, eval record.

**Out:** any core change (`graph.py`, `resolution.py`, `retrieval.py` stay
untouched — alias assertions use the existing additive `Resolution` layer from
the vertical side; promoting declared-alias support into the core waits until a
second vertical needs it); embeddings/semantic retrieval (reassessed, ADR 0010);
new synthetic ownership cases (the gold cases measure this path; extending the
synthetic battery is watched under ADR 0007 trigger 2 and revisited at close);
business vertical (no alias data exists there).

## Eval impact

**devex gold coverage 0.917 → 1.000** (the intended movement, recorded with
`--record --note`). Devex gold quality must stay 1.000 with the *stronger*
case-04 expectation ("Aiko Tanaka", the answer the miss used to withhold).
All faithfulness numbers stay 1.000 (new claims are verbatim snippets — shape
1); business battery untouched. Synthetic devex battery unchanged (routing
precedence keeps rca/summary/refusal cases on their paths — pinned by tests).

## Risks / open questions

- The alias-resolved cluster must not over-merge: an alias that equals another
  service's name would bridge entities. Guarded by exact normalized-equality
  matching (not similarity) and the existing cross-service disjointness test.
- Renaming gold case 04 (`..._known_miss` → `04_notifications_oncall`) changes
  a gold file: recorded here, question/engine/expected_support unchanged,
  expectation strengthened — the honest direction.
- The component row's text changes (it now states the alias), which slightly
  shifts BM25 statistics for lexical lookup — covered by the full battery run;
  any unexpected movement is a regression to fix, not re-record.
