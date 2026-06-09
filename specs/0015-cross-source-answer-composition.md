# 0015. Cross-source answer composition

- **Phase / milestone:** Phase 1 — The thin vertical slice. Unit 5. This is the **Phase 1 milestone**: "a person can ask one realistic cross-source question and get a sourced answer" (ROADMAP Phase 1; CAPABILITIES Pillar 3).
- **Issue:** (none yet)
- **Status:** draft

## Problem

The engine can now ingest both modalities, resolve cross-source entities (Unit 4),
and retrieve lexically (Unit 3) — but no single answer yet *combines* a database
row and a document clause about the **same** entity. Lexical retrieval can't:
asking about "Müller Logistik" surfaces the customer rows, not the agreement,
because it doesn't know they are one entity. This unit closes that gap by
**composing an answer over the knowledge graph**: resolve the question to an
entity, gather its evidence across both sources, and return a grounded answer
whose claims trace to a row *and* a clause. This is the payoff the graph was built
for, and it brings back the bounded synthesis Unit 3 honestly deferred.

## Acceptance criteria

- [ ] Given a question that names an organization, the system **resolves it to a
      graph entity** (cluster) by reusing the ADR-0004 name matcher (umlaut/case
      fold + similarity, `DEFAULT_RESOLUTION_THRESHOLD`); best match at/above
      threshold wins, otherwise **principled refusal** (no entity).
- [ ] It **gathers the entity's cross-source evidence** via the graph: the
      entity's structured rows (its customer/address nodes + sales documents
      reached through structural edges) and its **document clauses** (via Unit 4
      `Mention`s).
- [ ] It composes a **single answer** whose claims span **both** sources — at least
      one claim grounded in a SALT **row** and at least one in a document
      **clause** — each carrying claim-level provenance (source + locator),
      reusing `Claim`/`Answer`.
- [ ] **Bounded, sourced synthesis:** a deterministic aggregate over the entity's
      **homogeneous** structured rows (total net order value = sum of its sales
      rows) where **every summand is cited**; if the rows are not comparable (e.g.
      **mixed currencies**) it does **not** invent a total — it says so / reports
      per-currency, honestly.
- [ ] **Principled refusal** when the question resolves to no entity, or the entity
      has no relevant evidence — never a guess.
- [ ] A realistic cross-source question about **Müller Logistik** is answered
      **end-to-end** (its orders + total *and* its master service agreement's
      renewal terms), each claim sourced to a row or a clause — demonstrated via a
      runnable surface.
- [ ] The composition engine stays **vertical-neutral** (operates on graph
      entities/edges/mentions, not SALT-specific column logic). Gate green
      (CI-equivalent); `tessera-eval` still reports "no gold set evaluated yet".

## Scope

**In:** an entity-centric composition path — resolve question→entity, traverse the
graph for cross-source evidence, compose a grounded multi-source answer with one
sourced deterministic aggregate; principled refusal; a runnable demo of the Müller
cross-source question; tests.

**Out:** **general multi-step / multi-entity reasoning** and chains across several
entities (Phase 2); **question routing** (simple-vs-hard dispatch — Phase 2; this
unit adds the composition path, not a router that *chooses* it); **conflicting-
evidence reconciliation** (Phase 2); aggregates beyond a single sourced sum/count
over comparable rows; **LLM/semantic** anything (consistent with ADR 0003);
improving Unit 4 **mention recall** (the Lumière-style miss is inherited and
named, not fixed here); new ingestion, graph, or resolution mechanics.

## Eval impact

No number yet — 0 gold cases until Unit 6. But this delivers the **answer shape
the faithfulness metric will score**: a multi-source answer where every claim must
be supported by its cited row/clause. It is the honest target Unit 6 measures, and
the aggregate's "every summand cited" rule is the faithfulness contract made
concrete. Justified "none now" because the harness has no gold set yet.

## Risks / open questions

- **No ADR expected** — builds on ADR 0002 (provenance), 0003 (no LLM/semantic),
  0004 (graph + matcher). Confirm at `/plan`; if a real fork appears (e.g. how the
  aggregate handles units/currency, or how question→entity ambiguity is resolved),
  note it rather than bury it.
- **Question→entity precision.** A question naming "Müller Logistik" must hit the
  Müller cluster, not "Nordwind Logistik" — same precision concern as Unit 4;
  mitigated by the threshold + best-match, and honest when ambiguous.
- **Inherited mention-recall limitation.** If an entity's document reference was a
  Unit-4 miss (e.g. "Lumière Énergie"), composition simply has no clause to show —
  an honest gap, surfaced not hidden.
- **Synthesis boundary.** The single sourced aggregate must not creep into general
  reasoning; the mixed-currency refusal keeps it honest and bounded.
- **Surface/CLI shape.** Whether composition is a new entry point or routed from
  the existing CLI is a `/plan` decision (routing proper is Phase 2).
