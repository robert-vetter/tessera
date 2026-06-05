# 0010. Structured ingestion — synthetic SALT-shaped data into a common internal representation

- **Phase / milestone:** Phase 1 — The thin vertical slice (Business Data Copilot). Milestone: "universal ingestion working for **one** structured source," and the start of the common internal representation (`docs/CAPABILITIES.md` Pillar 1).
- **Issue:** (none yet)
- **Status:** draft

## Problem

Phase 0 proved the path *question → evidence → grounded answer with provenance*
against **hardcoded** evidence in `src/tessera/knowledge.py`. Phase 1's first
real step is to make that evidence come from an actual ingested source. This unit
ingests a structured dataset (the structured half of the slice) through one
intake path into a **common internal representation** that preserves enough
origin metadata to reconstruct provenance later — the substrate every later unit
(documents, retrieval, graph, eval) grows on. It is the structured source only;
the unstructured source is Unit 2.

**Data-source decision (recorded honestly).** The intended source was SAP's
**SALT** ERP dataset, but its data files are **access-gated** on Hugging Face
(HTTP 401), and redistributing a derived sample of a gated dataset is legally and
ethically murky — and would break the repo's clone-and-run guarantee. So this
unit uses a **synthetic dataset built on SALT's exact schema** instead: same
tables, columns, and join keys, generated deterministically and committed. This
sidesteps gating entirely, keeps the repo clone-and-run, and — because we code
against SALT's real schema — leaves **ingestion of real SALT a documented
drop-in swap** with no engine/test changes if access is later obtained.

## Acceptance criteria

- [ ] A **deterministic synthetic dataset** lives under `data/salt_synthetic/` as
      committed CSVs using **SALT's real table/column/join structure**:
      `I_Customer`, `I_AddrOrgNamePostalAddress` (linked by `AddressID`),
      `I_SalesDocument`, `I_SalesDocumentItem` (linked by `SalesDocument`; items
      reference customers via `SoldToParty` / `ShipToParty` / `BillToParty` /
      `PayerParty`). A few hundred rows total; connected (every item references a
      generated customer; every customer has an address) — so the rows still join.
- [ ] The synthetic customer/address data contains **genuine entity-resolution
      difficulty** (not planted-easy): legal-form suffix variants
      (`GmbH`/`Gmbh`/`G.m.b.H`), abbreviations, typos, and differing address
      formats — so Unit 4's ER is a real problem.
- [ ] A committed, re-runnable **generator script** (`scripts/`, **stdlib only**,
      fixed seed) reproduces the dataset byte-for-byte. Anchor entities are
      selected deterministically by the same seed.
- [ ] `data/salt_synthetic/NOTICE` + `README` state the data is **synthetic,
      modeled on SALT's schema**, credit **SALT as the schema reference**, and
      note that **real-SALT ingestion is a documented drop-in** (same CSV shape,
      gated by HF access only). The synthetic data is our own (no CC-BY-NC-SA
      encumbrance); code stays MIT.
- [ ] A **common internal representation** (vertical-neutral, in the engine, not
      in any source-specific module) carries, for every ingested unit,
      **retrievable origin metadata**: source identifier, a **modality-agnostic
      in-source locator** (here: table + row; shaped to also hold a document's
      page/line/chunk in Unit 2 without restructuring), and ingestion timestamp.
      It extends/supersedes the Phase 0 `EvidenceRecord` so that "no information
      enters without an attached, retrievable origin" (Pillar 1) holds **by
      construction**.
- [ ] A **structured ingester** reads the committed CSVs (stdlib `csv`, no heavy
      runtime dep) and yields these records into a `KnowledgeBase`, with **stable
      ids** (re-ingesting yields identical records). The ingester is
      **schema-faithful** — swapping in real SALT needs no ingester change.
- [ ] The engine answers the demo question from **ingested** data: the hardcoded
      `EvidenceRecord`s in `knowledge.py` are gone, and the evidence behind the
      answer traces to actual ingested rows (source + locator visible in output).
- [ ] Tests assert the invariants: (a) **every ingested record has non-empty
      origin metadata**; (b) ingestion is deterministic (stable ids across runs);
      (c) the demo answer's claims trace to ingested records; (d) refusal still
      triggers for unsupported questions; (e) the dataset actually contains the
      ER-difficulty variant forms (so Unit 4 has signal); (f) a document-style
      locator constructs in the **same** locator type (forward-compat proof).
- [ ] An **ADR** records the common ingestion/provenance representation. It must
      spell out **rejected alternatives** (bare `source: str`; flat optional
      fields → None-soup; stringly-typed locator), not just the chosen design,
      and show that the modality-agnostic locator (structured table+row now,
      document page/line/chunk in Unit 2) was deliberate forward-compat. `/verify`
      green; README documents how to run.

## Scope

**In:** the committed synthetic SALT-shaped dataset + generator script +
NOTICE/README; the common internal representation with origin metadata; a
schema-faithful structured ingester; re-pointing the demo answer onto ingested
evidence; tests for the origin/determinism/ER-difficulty/forward-compat
invariants; the ADR.

**Out:** the **unstructured source** (Unit 2); **retrieval** — the matcher stays
the Phase 0 deterministic keyword approach, now over ingested evidence (Unit 3);
the **knowledge graph / entity resolution** itself (Unit 4 — this unit only
*plants the difficulty*, it does not resolve it); the **eval harness** (scaffold
is Unit 1b, real metric Unit 6); any **LLM call**; **incremental re-ingestion /
dedup-on-update** (a Pillar 1 capability deferred — clean load only); NL
understanding; SALT-KG metadata graph (noted as a candidate reference for the
Unit 4 graph ADR, not used here); ingesting the **real** SALT dataset (documented
drop-in, gated by HF access).

## Eval impact

No faithfulness number yet — the harness is Unit 6. This unit replaces hardcoded
evidence with **genuinely-sourced, origin-tagged evidence**, the substrate the
faithfulness metric will later measure ("every claim supported by its cited
evidence, traceable to a real source row"). The eval **scaffold** ("no gold set
evaluated yet") lands in Unit 1b.

## Risks / open questions

- **ADR needed** — the common ingestion/provenance representation is load-bearing
  for every later unit; recorded via `/adr`, with rejected alternatives spelled
  out.
- **Synthetic realism.** Risk that synthetic data is too clean to exercise Unit
  4's ER. Mitigated by the ER-difficulty acceptance criterion + a test asserting
  variant forms are present.
- **Schema fidelity to SALT.** The drop-in promise holds only if our CSVs match
  SALT's real columns/keys. Mitigated by modeling the verified schema
  (`I_Customer`/`I_AddrOrgNamePostalAddress`/`I_SalesDocument`/`I_SalesDocumentItem`,
  `AddressID`, `SalesDocument`, party-role fields).
- **Representation over-reach** — risk of building Unit 4's graph here. Mitigated
  by keeping the representation a flat, origin-tagged record; relationships are
  later units.
- **Honest labeling.** Data under `data/salt_synthetic/` must be unmistakably
  flagged synthetic (dir name + NOTICE + generator) so no reviewer mistakes it
  for real SALT or assumes mishandled gated data.
