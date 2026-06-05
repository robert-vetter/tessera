# 0012. Unstructured ingestion — documents through the same door

- **Phase / milestone:** Phase 1 — The thin vertical slice (Business Data Copilot). Unit 2. Milestone: "universal ingestion working for **one** unstructured source," completing Pillar 1's "structured and unstructured arrive through the *same* door — neither privileged."
- **Issue:** (none yet)
- **Status:** draft

## Problem

Unit 1 brought a structured source into the common origin-tagged representation.
Pillar 1 requires the unstructured side to arrive through the **same intake
path** — not a parallel mechanism — so that later units (retrieval, graph, entity
resolution, answers) treat a contract clause and a database row as equal
citizens. This unit adds a small corpus of authored business documents
(agreements / correspondence) and ingests them via the **same `Ingester`
contract**, emitting evidence records with the **`doc-span` `Locator`** kind that
ADR 0002 already provides — so no representation change is needed, and the
forward-compat claim made in Unit 1 is now cashed in.

Crucially, the documents must reference the **actual** synthetic SALT customers
using their real **name variants** (the address-master spellings, abbreviations,
typos already in `data/salt_synthetic/`). That makes the future cross-source link
and Unit 4 entity resolution a *genuine* problem, not a planted exact-string match.

## Acceptance criteria

- [ ] A small corpus of authored unstructured documents (**markdown / plain
      text**) lives under `data/business_docs/`, committed, with a short README
      noting they are synthetic and reference the synthetic SALT customers.
- [ ] Some documents reference **real** synthetic SALT customers under **variant
      forms** (e.g. the address-master spelling or an abbreviation), so resolving
      them to the customer-master record is genuine ER work — not an exact match.
- [ ] A **document ingester** implements the same `tessera.ingestion.Ingester`
      contract, reading the committed docs and emitting `EvidenceRecord`s whose
      `Origin.locator` is `kind="doc-span"` with an in-document position (line
      span + chunk index). It comes through the **same intake path** as the
      structured source; the engine stays source-neutral.
- [ ] Chunking is **deterministic** (e.g. blank-line-separated blocks), ids are
      **stable** (e.g. `<file>:chunk<n>`), and `ingested_at` is a committed
      snapshot date — so re-ingestion is byte-stable, like Unit 1.
- [ ] The demo knowledge base now ingests **both** structured and document
      evidence, and a **document-grounded** question returns a claim whose
      provenance is a specific **document span** (file + line/chunk), visible in
      the rendered output — proving the unstructured path end-to-end, symmetric
      to Unit 1's structured path.
- [ ] Tests assert the invariants: every document record has a `doc-span` origin;
      ingestion is deterministic; ids are unique; at least one document references
      a known customer under a variant form (ER-readiness); a document-grounded
      answer traces to a doc span; refusal still triggers.
- [ ] Gate green via the **CI-equivalent** commands; `tessera-eval` still reports
      "no gold set evaluated yet"; README documents the document source.

## Scope

**In:** the authored markdown corpus + README; a document ingester via the
`Ingester` door using `doc-span` locators; deterministic chunking; demo wiring of
one document-grounded fact; tests; README.

**Out:** **PDF / office / binary parsing** (this unit is markdown/plain-text only
— one unstructured format, honestly; richer formats are later breadth);
**retrieval** (Unit 3 — matcher stays the deterministic keyword approach over
ingested evidence); the **knowledge graph and actually resolving** entities
across sources (Unit 4 — this unit only *plants* the genuine link); **single
claims citing both a row and a clause** (Unit 5); LLM-based extraction; OCR;
incremental re-ingestion / dedup. **No new representation** (conforms to ADR
0002) → **no ADR**.

## Eval impact

None yet — the harness has 0 gold cases until Unit 6, so there is no number to
move. This unit adds the *second modality's* sourced evidence the faithfulness
metric will eventually measure, and exercises the `doc-span` locator the metric's
provenance checks will rely on.

## Risks / open questions

- **Locator labels for documents.** Markdown has no real pages, so the `doc-span`
  parts will be line span + chunk index (`page` is reserved for paginated formats
  like PDF, out of scope). This fits ADR 0002's open `Locator.parts` with no
  change — confirm at `/plan`.
- **Where generic chunking lives.** Blank-line chunking is source-neutral and
  could sit in `ingestion.py` (engine), with only document-specific knowledge in
  the source module — keeps the engine general. Decide at `/plan`.
- **Document realism.** The docs must reference customers under variants that are
  recognisable yet non-trivial; mitigated by reusing the exact variant forms
  already present in `data/salt_synthetic/` (so Unit 4 has a real, checkable link).
