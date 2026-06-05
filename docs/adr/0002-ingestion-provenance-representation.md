# 0002. The common ingestion / provenance representation

- **Status:** accepted
- **Date:** 2026-06-05

## Context

Phase 1 brings real ingestion. Every piece of evidence that enters Tessera must
carry "enough origin metadata to reconstruct provenance later" (CAPABILITIES.md
Pillar 1), and it must do so for **both** modalities — structured rows now
(Unit 1) and document spans next (Unit 2) — without the record shape being
redesigned in between. This representation is load-bearing: retrieval (Unit 3),
the knowledge graph (Unit 4), and the faithfulness metric (Unit 6) all read it.
The Phase 0 `EvidenceRecord` had only a free-text `source: str`, which was honest
for a hardcoded skeleton but cannot pin *where within a source* a fact sits, nor
do so uniformly across modalities. We need a shape that is precise, reproducible,
and forward-compatible, decided now because changing it later means rewriting
every consumer.

## Decision

Evidence is represented as an `EvidenceRecord(id, origin, text)`, where:

- **`id`** is derived from the source's natural key (e.g. `I_Customer:0010000007`),
  so it is stable across re-ingestions rather than tied to row position.
- **`origin`** is an `Origin(source, locator, ingested_at)`. Constructing a record
  without an origin is impossible, so Pillar 1's "no information without a
  retrievable origin" holds **by construction**, not by convention.
  - `source` — a human-readable source identifier (`"salt_synthetic/I_Customer.csv"`).
  - `ingested_at` — the **data snapshot date**, not wall-clock time, so provenance
    metadata is deterministic and the eval is reproducible.
  - `locator` — a **modality-agnostic, kind-tagged** `Locator(kind, parts)`, where
    `parts` is an ordered tuple of `(label, value)` string pairs. A structured row
    is `kind="table-row"`, `parts=(("table","I_Customer"),("row","12"))`; a
    document span (Unit 2) is `kind="doc-span"`,
    `parts=(("page","3"),("line","10"),("chunk","2"))`. Consumers render `parts`
    uniformly and **never branch on `kind`**, so a new modality adds a `kind`
    value without touching the record or any consumer. This forward-compatibility
    is deliberate and is proven in code today by `test_locator_is_modality_agnostic`.

The engine (`grounding.py`, `ingestion.py`) stays source-neutral; per-source
schema knowledge lives under `tessera.sources`. Because the structured ingester
is written against SALT's real schema, ingesting real SALT is a drop-in.

## Consequences

- **Easier:** every claim already traces to an exact `(source, locator)` — the
  substrate the faithfulness metric needs is in place from the first real data.
- **Easier:** Unit 2 adds document evidence with no change to `EvidenceRecord`,
  `Origin`, downstream rendering, or the graph — only a new `Locator` kind and a
  new ingester.
- **Easier:** deterministic ids + snapshot-date timestamps keep ingestion
  reproducible, so the eval can rest on stable inputs.
- **Harder / accepted cost:** `Locator.parts` is loosely typed (`tuple[tuple[str,
  str], ...]`) rather than a per-modality typed schema. We accept weaker static
  guarantees on locator contents in exchange for never having to restructure the
  origin field. If a locator kind later needs validation, it can gain a typed
  constructor (as `Locator.table_row` already is) without changing the field.

## Alternatives considered

- **Keep `source: str` free-text only (the Phase 0 shape).** Rejected: it cannot
  express *where within a source* a fact lives, so provenance could not point at a
  specific row or page; and parsing structure back out of a human string is
  fragile. It was right for a hardcoded skeleton, wrong for real ingestion.
- **Flat, optional per-modality fields on the record** (`table`, `row`, `page`,
  `line`, `chunk`, all `| None`). Rejected: produces "None-soup" where most fields
  are null for any given record, invites consumers to branch on which fields are
  set, and grows a new nullable column for every future modality — the opposite of
  forward-compatible.
- **A stringly-typed locator** (e.g. `locator="page=3;line=10"`). Rejected: it
  pushes parsing onto every consumer, has no agreed grammar, and silently tolerates
  malformed values — exactly the untraceable ambiguity provenance must avoid.
- **A closed tagged union of typed locator classes** (`StructuredLocator |
  DocumentLocator | ...`). Reasonable, and stronger typing, but every new modality
  edits the union and consumers risk non-exhaustive matches. We chose the
  kind-tagged `parts` shape for uniform rendering with zero consumer changes; a
  typed constructor per kind recovers most of the safety where it matters.
