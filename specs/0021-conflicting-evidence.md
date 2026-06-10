# 0021. Conflicting evidence surfaced, never silently mixed

- **Phase / milestone:** Phase 2 — deliberately tricky cases: conflicting sources
- **Issue:** (none)
- **Status:** implemented

## Problem

The project brief's first named failure mode is *silent source mixing*: two
sources disagree and the system blends or picks one without saying so. The
corpus so far contains no disagreement, so the behavior is untested and
unmeasured. This unit adds a **deliberate, deterministic conflict** to the
corpus — an amendment that moves Müller Logistik's renewal date (1 February)
against the MSA (1 August) — and teaches the engine to **surface** the
disagreement: a conflict claim naming both values, citing both clauses, and
refusing to assert a single date.

## Acceptance criteria (decided in autonomous mode)

- [ ] `data/business_docs/mueller_logistik_amendment.md` states a renewal date
      conflicting with the MSA; MANIFEST updated; ingestion deterministic.
- [ ] `conflicts.py`: renewal-date extraction + `find_renewal_conflict` —
      returns a conflict claim citing **every** date-stating clause when the
      stated dates disagree; `None` otherwise. Scope is honestly narrow: one
      conflict class (renewal dates), not a general contradiction detector.
- [ ] Composition appends the conflict claim for an affected entity.
- [ ] Verifier learns the conflict shape: quoted values must each be stated by
      a distinct cited clause and must actually disagree — adversarially
      tested (agreeing citations or unquoted values are caught).
- [ ] Gold case 07 covers the conflict path; existing gold cases stay green.

## Scope

**In:** the conflicting document, detection + surfacing, verifier shape, gold
case, tests. **Out:** general contradiction detection (NLI/LLM — ADR 0006
triggers), structured-vs-document conflicts (future class, same pattern),
conflict *resolution* (deliberately never: surfacing is the feature).

## Eval impact

Gold grows to 7 cases. Faithfulness floor now covers conflict claims (provably
fallible). Coverage/quality recomputed over the larger set — expected ≈ same
(the Lumière miss remains the one gap until spec 0024).

## Risks

- The amendment's chunks join the retrieval corpus and could shift BM25 top-5
  for existing lookup cases — checked against the gold set in this unit.
