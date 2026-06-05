# 0013. Lexical retrieval over ingested evidence

- **Phase / milestone:** Phase 1 — The thin vertical slice. Unit 3. Milestone: "grounded conversational answers with claim-level provenance for a narrow class of questions" — make the answer come from *retrieved* evidence, not a hand-authored question→claim map.
- **Issue:** (none yet)
- **Status:** draft

## Problem

Today `answer()` is driven by the Phase-0 keyword `Fact` mechanism: each demo
question is hand-mapped to a **precomputed** claim. That is not retrieval — it
does not scale past the demo, it cannot be measured, and the claim text is
authored rather than built from evidence. This unit replaces it with a **real
lexical retriever** that, given a question, selects the most relevant ingested
`EvidenceRecord`s across **both** sources (structured rows + document chunks) and
builds the answer **from that retrieved evidence**. When nothing is relevant
enough, it refuses on a principled, score-based basis. This is the first unit
whose behaviour the coverage metric will eventually measure.

Per the approved plan, retrieval is **lexical-first**; semantic/embedding
retrieval is deliberately deferred and recorded in an ADR.

## Acceptance criteria

- [ ] A **lexical retriever** `retrieve(question, kb, k)` returns the top-`k`
      `EvidenceRecord`s ranked by relevance, scored across **both** modalities
      (SALT rows and document chunks). Pure-stdlib (e.g. TF-IDF / BM25-style term
      scoring), **deterministic** (stable tie-breaking), **no model or network**.
- [ ] `answer()` is **driven by retrieval**: it surfaces the retrieved evidence as
      claims, each carrying claim-level provenance to the record(s) it came from.
      When the best score is below a documented relevance **threshold**, it returns
      a **principled refusal** rather than surfacing irrelevant evidence.
- [ ] The hand-authored keyword `Fact` mechanism and all **precomputed claim
      text** are **removed**; `knowledge.py` becomes pure knowledge-base assembly
      (ingest both sources → records). No fabricated or pre-authored answer text
      remains anywhere.
- [ ] Retrieval **spans both sources**, shown end-to-end via the CLI: a renewal
      question surfaces the MSA clause (document); a customer-orders question
      surfaces the relevant sales rows (structured).
- [ ] Tests: a known-relevant record ranks above an irrelevant one; a
      document-relevant query returns the doc chunk and a row-relevant query
      returns the row; the refusal path triggers below threshold; **every surfaced
      claim cites its source record** (provenance invariant); retrieval is
      deterministic.
- [ ] An **ADR** records **lexical-first** retrieval and the deliberate deferral
      of semantic/embedding retrieval, with rationale and rejected alternatives.
- [ ] Gate green (CI-equivalent commands); `tessera-eval` still reports "no gold
      set evaluated yet"; README updated.

## Scope

**In:** the lexical retriever; `answer()` rewired to retrieve-then-surface, with a
score-based refusal threshold; removal of `Fact`/precomputed claims; KB-assembly
cleanup in `knowledge.py`; tests; the ADR; README.

**Out:** **semantic / embedding retrieval** and any **LLM** (ADR-deferred);
**synthesis / aggregation** of multiple records into a computed answer — e.g.
*summing* order values into "combined value EUR 45,000" — which is multi-step
reasoning (Phase 2), not retrieval; **question routing** simple-vs-hard (Phase 2);
**cross-source entity resolution** (Unit 4 — retrieval may surface records from
both sources but does **not** link "Mueller Logistik Gmbh" to its customer row);
conversational follow-ups; heavy ranking-quality tuning beyond a sensible
baseline.

**Honesty note:** because synthesis is out of scope, the demo answer *changes
character* — instead of a precomputed "combined value is EUR 45,000," the system
surfaces the relevant sourced records for the question. That is more honest (it
retrieves evidence; it does not yet do arithmetic) and is what makes retrieval
real and measurable.

## Eval impact

No number yet — 0 gold cases until Unit 6. But this is the capability the
**coverage** metric (did we find the evidence that was there?) and the refusal
behaviour will measure; it replaces an unmeasurable hand-map with a real,
score-driven path. The threshold choice here directly shapes coverage-vs-refusal,
to be calibrated when the gold set lands.

## Risks / open questions

- **ADR needed** — lexical-first, embeddings deferred.
- **Refusal threshold.** The hardest choice: too low never refuses, too high
  over-refuses. Needs a defensible, documented default now, to be calibrated
  against the gold set in Unit 6. Decide the default at `/plan`.
- **Claim = retrieved snippet.** Without an LLM, a surfaced claim's text is (or
  derives from) the evidence snippet itself. Honest but blunt; richer synthesis is
  Phase 2. Confirm the representation at `/plan`.
- **Variant blindness.** Lexical scoring will miss variant forms ("Müller" vs
  "Mueller") that only fuzzy/semantic matching or entity resolution (Unit 4) bridge.
  Basic normalization (casefold, umlaut-fold) helps; the limitation is real and
  should be named in the ADR as a reason the deferral is revisitable.
