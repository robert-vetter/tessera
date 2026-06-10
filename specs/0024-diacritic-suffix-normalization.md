# 0024. Close the Lumière coverage gap: diacritic folding + suffix-tolerant mentions

- **Phase / milestone:** Phase 2 — milestone: "the trust metric has visibly
  improved since Phase 1"
- **Issue:** (none)
- **Status:** implemented

## Problem

Coverage has carried one documented gap since Phase 1: the Lumière Énergie
letter's clauses never link to the entity, so composed answers omit them
(gold coverage 0.929 → 0.938 as the set grew). Diagnosis (verified against
the graph, not assumed) shows **two** deterministic causes:

1. `normalize()` folds German umlauts but **deletes** other diacritics, so
   `"Lumière"` → `"lumire"` while `"Lumiere"` → `"lumiere"` — the same name
   fails to match itself across accent variants.
2. Every master-data variant carries the legal suffix (`SARL`/`S.A.R.L.`),
   while the letter names the company without it — full-name containment can
   then never match, exactly the limitation `link_document_mentions`
   documented.

This is the metric-driven improvement ADR 0004 promised: the coverage number
identified the miss; the fix is deterministic and additive.

## Acceptance criteria (decided in autonomous mode)

- [ ] `normalize()` folds diacritics to base letters (NFKD + combining-mark
      strip) **after** the German digraph folding (`ü`→`ue` preserved — the
      data's Müller/Mueller variants depend on it).
- [ ] Document-mention linking also tries each name with a known legal suffix
      stripped (≥ 8 normalized chars must remain); such mentions carry
      **reduced confidence (0.9)** and a reason naming the stripped form —
      the assertion stays inspectable per ADR 0004.
- [ ] The Lumière letter links; composed answers cite its clauses; **gold
      coverage reaches 1.000** and the run is recorded to the history journal
      (the milestone's "visibly improved", literally visible).
- [ ] No false merges: existing resolution proof tests (Bayerische 4-way,
      Müller ≠ Nordwind, reversibility) stay green; the
      previously-documented-miss test is updated to assert the link now
      exists, citing this spec.
- [ ] ADR 0004 gains an append-only addendum recording the refinement.

## Scope

**In:** normalization + mention matching + tests + history record + ADR
addendum. **Out:** multi-field (name+address) matching, embeddings/ML (ADR
0004 future work — the deterministic fix suffices for this gap).

## Eval impact

Gold coverage 0.938 → **1.000** (the Lumière expected-support id is now
cited). Faithfulness must stay 1.000 (new clause claims are snippet-shape).
Synthetic battery re-verified green.

## Risks

- Folding increases name-pair similarity scores slightly; the proof tests and
  the threshold (0.85, unchanged) guard against new false merges.
- Suffix stripping is confined to *mention* linking (doc ↔ entity), not to
  entity resolution itself — deliberately small blast radius.
