# 0003. Lexical-first retrieval; semantic retrieval deferred

- **Status:** accepted
- **Date:** 2026-06-05

## Context

Unit 3 replaces the Phase-0 hand-authored question-to-claim map with real
retrieval: given a question, select the most relevant ingested evidence records
(across structured rows and document chunks) and build the answer from them. We
must choose *how* relevance is scored. The realistic options are classical
lexical scoring, learned semantic embeddings, or a hybrid. This choice shapes
dependencies, determinism, and what the eval can measure — and it is the kind of
direction worth recording even though it is revisitable.

Constraints that weigh on the decision: the project must stay **clone-and-run and
deterministic** (the eval rests on reproducible inputs), must keep a **portable
local mode with no mandatory cloud/model dependency** (CLAUDE.md), and has **no
faithfulness/coverage number yet** (Unit 6) against which to justify added
complexity.

## Decision

Retrieval is **lexical-first**: Okapi BM25 over tokenized record text
(casefold + umlaut-fold + alphanumeric split + a small stop list + a crude
trailing-`s` fold), pure-stdlib, deterministic. A question is **refused** when no
record shares any content token with it (top score 0), so refusal is principled
and threshold-free rather than a tuned magic number.

**Semantic / embedding retrieval is deliberately deferred.** We will revisit it
when there is a measured reason to — see the revisit trigger below — at which
point SAP's Generative AI Hub embeddings + HANA Cloud vector store are the
intended target, with the lexical path retained as the portable local fallback.

## Consequences

- **Easier:** no model or network dependency; fully deterministic and offline, so
  the repo stays clone-and-run and the eval rests on reproducible retrieval.
- **Easier:** the refusal rule is transparent (no opaque threshold), which keeps
  the future coverage metric auditable.
- **Harder / accepted cost — variant blindness.** Lexical scoring matches surface
  forms, so it does **not** bridge entity variants: a question about "Müller
  Logistik" will rank the customer/address *rows* that contain those tokens, and
  will **not** by itself recognise that the agreement naming "Mueller Logistik
  Gmbh" is the same entity. We knowingly accept this for now. **Resolving entity
  variants to one identity is not the retriever's job — it belongs to the graph /
  entity-resolution layer (Unit 4).** Likewise, ranking is term-frequency driven,
  so boilerplate that repeats query terms can outrank the substantive clause; a
  question phrased around the clause's own terms retrieves it well.
- **Accepted:** no synthesis. A surfaced claim's text *is* the evidence snippet;
  computing aggregates or composing prose is multi-step reasoning (Phase 2).

## Revisit trigger

Reconsider semantic/embedding (or hybrid) retrieval when the **coverage metric
(Unit 6) shows lexical retrieval missing evidence that was present** — in
particular, relevant records lost to vocabulary mismatch or entity-variant
phrasing that entity resolution (Unit 4) does not already absorb. The decision is
explicitly provisional and measured, not permanent.

## Alternatives considered

- **Semantic / embedding retrieval now.** Rejected as premature: it adds a model
  dependency and non-determinism (and, on the SAP target, a cloud dependency)
  *before* we have any coverage number to justify the cost or even confirm lexical
  retrieval is insufficient. It also undercuts the clone-and-run/offline guarantee.
- **Hybrid (lexical + semantic).** Rejected for now as more complexity than a
  baseline warrants: without the metric in place we cannot tune the blend
  honestly. It remains the likely end state once measured.
- **Keep the Phase-0 keyword `Fact` map.** Rejected: it is not retrieval — every
  answer is hand-authored, it does not scale past the demo, and it cannot be
  measured. Replacing it is the whole point of this unit.
