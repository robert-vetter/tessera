# 0130. S1 — real SALT data: grounded, provenance-complete, on the actual dataset

- **Phase / milestone:** SAP track S1 (ROADMAP2; the highest-credibility
  SAP proof point). Unblocked 2026-07-04 when the maintainer's gated
  Hugging Face access to `SAP/SALT` came through and the dataset was
  pulled to `var/salt_real/` (gitignored, 116 MB, 8 parquet tables).
  Autonomous per CLAUDE.md; the shaping decision (below) was the
  maintainer's.
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Since Phase 1 the project has run on **synthetic** data built on SALT's
*schema*, with the real dataset a "documented drop-in, gated only by HF
access" (`data/salt_synthetic/NOTICE`). The access arrived — and
inspecting the real tables produced a **project-shaping finding** that
this unit both acts on and records honestly.

**The finding (measured 2026-07-04, evidence in the report):** real SALT
is **fully anonymized**. `I_Customer` is `(CUSTOMER, ADDRESSID)` — a
numeric code and an address id, **no name**. `I_AddrOrgNamePostalAddress`
— despite its name — has an `ADDRESSREPRESENTATIONCODE` that is empty on
**0 of 1,788,887** rows; the only content is `COUNTRY` (ISO code) and a
~20%-filled `REGION`. Across all 8 tables there is **no free-text
name/description/street/city column anywhere**; every entity is a code,
and linkage is by **exact foreign key**. This confirms the SALT-KG thesis
(MARKET §7: models "can't leverage relational semantics") on the real
data: **SALT's difficulty is relational, not lexical.**

**Consequence, recorded not hidden:** Tessera's name-similarity entity
resolution (ADR 0004/0018/0019/0020) has nothing to bite on in real SALT
— the "Müller/Mueller/GmbH-variant" ER is a capability the *synthetic*
corpus was built to exercise; it has no real-SALT analog. What real SALT
*does* support, and what this unit delivers, is **deterministic
FK-linked grounding with claim-level provenance over the actual gated
data** — the structural half of the engine, on real ERP records.

**Recorded decisions:**

1. **A bounded, connected slice — not the full 4.6M rows.** The
   in-process graph is a demo-scale structure (ADR 0004); a coherent
   slice of ~25 real customers, each with its resolvable address and its
   real sales documents/items (customers that appear as `SOLDTOPARTY`,
   of which 13,155 exist with resolvable addresses), is a genuine
   connected real-SALT subgraph and enough to prove grounding on real
   data. Scale to 139k customers is named future work, not this unit
   (the maintainer chose "build what really applies", not the scale
   variant).
2. **No real SALT data is committed — ever.** The gated dataset and any
   derived slice stay under `var/` (gitignored), exactly like M18's BYO
   workspaces and per the `NOTICE`'s redistribution rule. The committed
   artifacts are the *code path*, a *committable anonymized fixture* we
   author ourselves (real schema, coded values, no encumbrance — the
   `data/ingest_demo` precedent), and a *report* of the recorded run.
3. **Parquet → CSV slice at the boundary; the ingester stays stdlib.**
   `scripts/salt_real_slice.py` (needs `pyarrow`, a new opt-in `salt`
   extra) reads `var/salt_real/*.parquet`, extracts the connected slice,
   and writes plain CSV into `var/salt_real_slice/`. The new
   **`tessera/sources/salt_real.py`** ingester reads that CSV with the
   stdlib — no pyarrow, no name dependency — into `EvidenceRecord`s +
   FK structural edges, reusing the unchanged engine
   (graph/grounding/retrieval). CI tests it against the committed
   fixture; the real run points it at `var/`.
4. **Grounding, honestly scoped.** The answer for "what do we know about
   customer `<code>`?" composes: the customer row, its address
   (country/region) via the `located_at` FK, and its sales documents
   (currency, type, incoterms, creation date) via the `sold_to` +
   `line_of` FKs — **every claim citing a real SALT row's locator**. No
   invented names, no name-ER; a vertical-neutral lookup + FK traversal.
5. **Frozen core untouched; `sources/salt.py` (frozen, ADR 0008) NOT
   modified** — `salt_real.py` is a new file beside it. The six committed
   eval lines stay byte-identical (this unit adds a real-data path and a
   report; it does not touch the batteries).
6. **Light pre-merge review** (an ingester over foreign real data +
   control-character exposure from real strings): one focused
   correctness/robustness pass; findings fixed or recorded.

## Acceptance criteria

- [ ] `scripts/salt_real_slice.py` extracts a deterministic connected
      slice from `var/salt_real/` to `var/salt_real_slice/` (CSV);
      documented shape; `salt` extra added.
- [ ] `tessera/sources/salt_real.py` ingests the slice (stdlib) into
      records + FK edges; a vertical-neutral grounded answer for a named
      customer composes address + sales-doc claims, each with real
      provenance; unknown customer refuses.
- [ ] `data/salt_real_fixture/` — a small authored anonymized fixture in
      the real schema; `tests/test_salt_real.py` proves ingest + FK
      grounding + refusal over it (CI, no gated data).
- [ ] A **recorded real run** over `var/salt_real_slice/` captured into
      `docs/SALT_REAL.md`: the finding (with evidence), the method, the
      grounded answer for a real customer with its provenance trail, and
      honest limits (anonymized → no name-ER; bounded slice; not
      committed).
- [ ] `data/salt_synthetic/NOTICE` gets a one-line pointer to the report;
      `launch/sap/APPLICATION.md`'s SALT line upgraded from "ready to
      swap in" to the measured reality.
- [ ] Gate green; six eval lines byte-identical; frozen core untouched;
      CI key-free and gated-data-free.

## Scope

**In:** the slice script + `salt` extra, the `salt_real.py` ingester, the
committable fixture, tests, the report, the two doc touch-ups.
**Out:** committing any real SALT data; name-based ER on real SALT (has no
analog — recorded); the 139k-row scale test (named future work); a
`salt_real` eval battery (foreign data isn't committed — the report is the
proof, like M18's connect/smoke story); any change to `sources/salt.py`
or the frozen core.

## Eval impact

None on the six committed lines (additive real-data path + report). The
honest new *result* is qualitative: grounded, provenance-complete answers
on the actual SALT dataset, plus the recorded anonymization finding.

## Risks / open questions

- Real strings (even coded) are foreign input → the ingester neutralizes
  control characters on every ingested field (the M18 connect precedent),
  covered by a fixture test.
- `pyarrow` is heavy; it is strictly opt-in (`salt` extra), never in CI,
  imported only by the slice script.
- The slice must be **connected and deterministic** (stable customer
  selection, sorted) so the report's numbers are reproducible by anyone
  with gated access.
