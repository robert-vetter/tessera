# 0078. VATRegistration field + source wiring (registration-key ER)

- **Phase / milestone:** Milestone 10 — registration/tax-key entity resolution
- **Issue:** —
- **Status:** approved (autonomous mode; design recorded in **ADR 0020**)

## Problem

Multi-field name+address ER (M9) leaves one floor: two genuinely distinct firms with
the **same** name **and** the **same** address over-merge, because the address
*agrees*. Only an exact identity key separates them. This unit adds that key — the
field + the source wiring + the non-regression proof — so Unit 3 can append the
demonstration pair and measure the close.

## What this unit does

1. **The data.** `scripts/generate_salt_synthetic.py` adds a `VATRegistration` column
   to `I_Customer`, populated for **every** customer, **per canonical entity** (seed on
   the canonical name so duplicates share one VAT; seed on the unique customer id for
   the hand-appended same-name distinct firms — the M9 Hanseatic pair — so they get
   distinct VATs). A `_seen` guard makes a hash collision between two distinct seeds a
   build failure. Country-prefixed `<CC><9 digits>` (real `DE`-VAT shape for the demo
   firms; an honest synthetic stand-in elsewhere). Existing columns are byte-identical
   (the new column is appended; no existing cell changes); the address CSV is
   unchanged; MANIFEST counts are unchanged (no new rows in this unit).
2. **The source.** `sources/salt.py` attaches `vat_registration` to the customer node
   (its own column) and **denormalizes it onto the customer's linked address node**
   (via `AddressID`), so the key is on both nodes a same-address pair bridges through.
   `CUSTOMER_MATCH_FIELDS = ("vat_registration",) + ADDRESS_MATCH_FIELDS` — key first
   (most decisive); `build_demo_graph` defaults to it.
3. **The engine.** No behavior change. The one delta is honesty: `graph._merge_reason`
   generalizes the bridge wording "bridged by address" → "bridged by corroborating
   field" (`signal.detail` already names the field), so a key-bridged merge does not
   misreport "address". `resolution.py` is empty-diff.
4. **The proofs.** `test_vat_first_moves_no_cluster_on_existing_data` — resolved
   clusters are byte-identical between the VAT-first default and the M9 address-only
   path on the existing data (a mis-assigned VAT fails here). Abstract mechanism tests:
   the key decides above the address (split on different key despite agreeing address;
   merge on same key despite disagreeing address — the postal-override bonus); the
   same-key positive control merges; key-absent falls back to the address. Two M9
   reason-content tests updated to the field-general wording.

## Acceptance criteria

- [x] `VATRegistration` on every customer, per entity; existing columns byte-identical;
      address CSV + MANIFEST unchanged; generator deterministic + collision-guarded.
- [x] `vat_registration` on customer **and** denormalized address node;
      `CUSTOMER_MATCH_FIELDS` key-first; `build_demo_graph` default updated.
- [x] Engine behavior unchanged (`resolution.py` empty-diff; `graph.py` only the
      bridge-wording generalization); cluster signatures byte-identical (pinned).
- [x] All three batteries' eval numbers byte-identical (faithfulness 1.0); 319 tests;
      deterministic across `PYTHONHASHSEED` 0/1/42/2026.
- [x] **ADR 0020** records the design, the new floor, and the rejected alternatives.
- [x] Pre-merge adversarial multi-agent review (frozen-list source + VAT-first reason
      shift).

## Out of scope (this unit)

- The same-name/**same-address** demonstration pair + the measured before/after
  (Unit 3, spec 0079).
- The WRITEUP/README/CHANGELOG/STATUS close (Unit 4, spec 0080).
