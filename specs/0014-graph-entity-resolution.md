# 0014. Knowledge graph + cross-source entity resolution

- **Phase / milestone:** Phase 1 — The thin vertical slice. Unit 4. Milestone: "a first version of the knowledge graph with basic cross-source entity resolution between the two sources" (CAPABILITIES Pillar 2).
- **Issue:** (none yet)
- **Status:** draft

## Problem

Retrieval (Unit 3) surfaces records from both sources but cannot tell that
"Müller Logistik GmbH" (customer master), "Mueller Logistik Gmbh" (address
master), and the agreement naming the same firm are **one real entity** — that is
entity resolution, and it is the missing layer before any cross-source answer
(Unit 5) can combine a row and a clause about the same customer. This unit builds
a first knowledge graph over the ingested records and a **basic, honest,
cross-source entity-resolution layer** on top of it.

The hard part is doing resolution **without destroying or overclaiming**: merges
are fallible, so they must be inspectable, reversible, and explainable.

## Fixed design constraints (decided by the maintainer; see ADR 0004)

1. **Embedded / in-process graph** for the slice — not Neo4j, not HANA directly.
   HANA Cloud portability is documented future work.
2. **Resolution is a non-destructive layer over the raw nodes.** Raw records keep
   their identity and provenance untouched. A resolved-entity assertion says
   "these nodes refer to the same real entity" and carries (a) the reason (which
   fields matched, the score) and (b) a confidence. Removing an assertion leaves
   the raw data intact. Source nodes are never collapsed or overwritten.
3. **Deterministic, explainable string matching** (umlaut-fold, casefold, a
   deterministic similarity/edit-distance score) with an explicit per-match
   confidence. No embeddings/ML (future work, consistent with ADR 0003). Be honest
   about precision/recall.
4. **Scope ends at the graph + resolution.** Cross-source *answer composition* is
   Unit 5 and is not built here.

## Acceptance criteria

- [ ] An **embedded, in-process graph** holds nodes wrapping the ingested records
      (each node keeps its record id + provenance, **untouched**) and deterministic
      **structural edges** from the structured foreign keys (customer↔address via
      `AddressID`; sales-document↔customer via party role; item↔sales-document). No
      external graph database.
- [ ] A **non-destructive resolution layer**: pairwise `Resolution` assertions over
      organization-name-bearing nodes stating "these refer to the same real
      entity," each carrying **(a) a reason** (the matched fields, their normalized
      forms, and the similarity score) and **(b) a confidence**. Assertions are
      enumerable (**inspectable**) and removing one leaves raw nodes/records intact
      (**reversible**); nothing is collapsed or overwritten.
- [ ] **Deterministic, explainable matching**: umlaut-fold + casefold + a
      deterministic similarity score on the name fields, with a **documented
      threshold**. Pairs at/above threshold get an assertion (confidence = score);
      pairs below stay separate. No embeddings/ML.
- [ ] **Resolved entities are the clusters** (connected components of the
      assertions); each cluster traces to its member nodes and the per-link
      reasons + confidences.
- [ ] **Cross-source linking**: document chunks are linked to a resolved entity by
      the same deterministic matching of the entity's known name variants against
      the chunk text, with reason + confidence (this sets up Unit 5; **no answering
      here**).
- [ ] **Proof tests:** (a) the customer + address variants of *Bayerische
      Stahlwerke* (`Bayeriche`, `Bayersche`, `Bayerische`×2) resolve into **one**
      entity with traceable reasons + confidence; (b) `Müller Logistik GmbH`
      (customer) and `Mueller Logistik Gmbh` (address) resolve to one entity;
      (c) a genuine **non-match** — `Müller Logistik GmbH` vs `Nordwind Logistik
      GmbH`, which share "Logistik GmbH" — **stays separate** (no assertion);
      (d) removing an assertion leaves the raw nodes/records intact (reversibility).
- [ ] An **ADR** records the graph model + the merge/confidence design and
      documents HANA Cloud + embeddings/ML as future work. Gate green
      (CI-equivalent); `tessera-eval` still reports "no gold set evaluated yet".

## Scope

**In:** the in-process graph (nodes + structural FK edges, provenance preserved);
the non-destructive resolution layer (pairwise assertions, reasons, confidence,
derived clusters); deterministic string-matching ER over organization names
including document→entity linking; proof tests; the ADR; README.

**Out:** cross-source **answer composition** / graph-backed answering (Unit 5);
**embeddings/ML** resolution (ADR future work); a **persistent / Neo4j / HANA**
store (ADR future work); learned **NER** (document mentions are matched
deterministically against known entity names, not extracted by a model);
resolving **non-organization** entities (people, materials); tuning ER to
perfection — precision/recall are reported honestly, not maximized.

## Eval impact

None on the harness yet — 0 gold cases until Unit 6. This builds the entity layer
whose quality the Unit 6 metrics (and a possible ER precision/recall check) will
measure; it does not move a number now. The proof tests are an honest, if narrow,
statement of current behaviour on known variants and a known non-match.

## Risks / open questions

- **ADR needed** — graph model + merge/confidence design.
- **Precision vs recall.** Distinctive-token cases ("X Logistik GmbH") are exactly
  where a similarity threshold trades precision against recall. The ADR must state
  the measure, the threshold, and the observed behaviour honestly — no claim of
  perfection. The non-match test guards precision; over-tight thresholds would
  hurt recall on the Bayerische typos.
- **Similarity measure choice** (normalized edit-distance ratio vs token-based) —
  pick a deterministic, explainable one; decide at `/plan`, record in the ADR.
- **Document mentions without NER.** Matching known entity names against chunk
  text is deterministic but will miss mentions phrased unusually; an honest,
  named limitation.
