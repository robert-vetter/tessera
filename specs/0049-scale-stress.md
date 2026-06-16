# 0049. Scale stress: the trust path at volume, and the over-merge measured

- **Phase / milestone:** Milestone 5 — Hardening (spec 0043, unit 7)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

The WRITEUP names an honest limitation at full prominence: *"Scale behaviour
(retrieval quality, graph performance, ER precision under volume) is untested.
… hundreds of records, not millions."* The committed corpora are small (≈40
business entities) by design; nothing exercises the engine at volume, so two
questions are open: does the trust path stay **faithful** at scale, and does
deterministic ER stay **precise** as the number of similar names grows?

## Acceptance criteria

- [ ] A deterministic, seeded scale harness builds a large graph (180 distinct
      firms + an accented-variant cohort + hundreds of sales rows) through the
      **real** engine — `KnowledgeGraph`, `resolve_entities` at 0.85, the
      multi-step reasoners, and the same `is_supported` verifier the eval uses.
- [ ] **Precision and recall at volume:** 180 distinctive firms resolve into 180
      clusters (no transitive collapse; max cluster size 2), and every accented
      variant merges into its firm.
- [ ] **Faithfulness holds at volume:** a superlative ranking and a pairwise
      compare over the large graph emit only claims the verifier re-derives.
- [ ] **The over-merge risk is measured, not just noted:** a focused case shows
      that distinct firms sharing a long generic suffix with similar short stems
      ("… Logistik GmbH") transitively over-merge at the 0.85 threshold —
      turning the WRITEUP's "transitive over-merge remains possible in principle"
      into a reproduced fact.
- [ ] No eval battery, no committed corpus, no recorded-number change (the
      measurements are the test's assertions); all eight numbers unchanged.

## Scope

**In:** `tests/test_scale.py` — the scale harness and its four assertions
(precision/recall, faithfulness, the measured over-merge, a soft timing bound).

**Out:** growing the committed `data/salt_synthetic` corpus (its size is tuned
so the gold superlative/compare cases hold; scaling it would disturb the EUR
superlative winner and the pinned compare totals — the scale harness builds its
own in-memory corpus instead); a `scale` eval battery (the trust path is the
thing under test, not a new vertical to record); multi-field ER or an embedding
matcher to *fix* the over-merge (that is ADR 0004/0010 future work — this unit
*measures* the limit, it does not move the determinism line); retrieval-quality-
at-volume beyond what the reasoning path exercises (BM25 latency at millions of
records is genuinely out of reach with a synthetic corpus and stays named).

## Eval impact

None — no recorded number changes. The contribution is a **measurement**: the
engine is faithful and ER-precise over 180 entities with distinctive names, and
the deterministic threshold demonstrably over-merges generic-suffix firms at
volume. Both results are now reproducible facts in the suite rather than
unexamined assumptions.

## Risks / open questions

- The scale harness uses an in-memory corpus, so it does not exercise the file
  ingestion path at volume — acceptable, because the scale-sensitive components
  are resolution (the dominant cost and the over-merge source), reasoning, and
  the verifier, all of which it drives directly through the real engine.
- The over-merge finding sharpens an existing, documented limitation; it does
  **not** fire a new trigger by itself (the deterministic ER threshold is a known,
  named knob). The remedy — multi-field ER or embeddings — stays future work
  behind ADR 0004/0010, recorded in spec 0050's trigger status.
- 180 entities is "scale" relative to 40, not "millions"; the limitation remains
  honestly named in the WRITEUP, now with a tested floor under the claim.
