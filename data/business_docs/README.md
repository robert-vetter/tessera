# Business documents (synthetic)

The unstructured half of the Phase 1 slice: a small corpus of **authored**,
**synthetic** business documents — agreements and correspondence — ingested
through the same intake path as the structured SALT-shaped data (see
[`specs/0012-unstructured-ingestion-documents.md`](../../specs/0012-unstructured-ingestion-documents.md)).

Two properties are deliberate, and tested:

- **They reference the real synthetic SALT customers under *variant* forms** — the
  address-master spelling, a missing accent, the correct legal name where the ERP
  master has a typo — so tying a document back to its customer row is *genuine*
  entity-resolution work (Unit 4), not an exact-string match. At least one
  document (`bayerische_stahlwerke_terms.md`) uses a form that matches **no**
  customer-master record even after normalization, so only a real resolution step
  can link it.
- **They carry information the tables lack** — renewal clauses, payment terms,
  volume discounts, special conditions — for customers whose sales *are* in SALT.
  This gives later cross-source answers (Unit 5) two genuine halves to combine,
  not redundant restatement.

These documents are our own synthetic content, under the project's MIT license.
`ingested_at` for every chunk is the `snapshot_date` in `MANIFEST.json`, so
ingestion is deterministic.
