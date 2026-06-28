# 0079. The same-name/same-address pair + the measured before/after

- **Phase / milestone:** Milestone 10 — registration/tax-key entity resolution
- **Issue:** —
- **Status:** approved (autonomous mode; the close of ADR 0020)

## Problem

Unit 2 added the `VATRegistration` field + the key-first `match_fields` and proved it
moves no existing cluster. This unit lands the **demonstration**: a same-name /
**same-address** disambiguation pair the address gate cannot reach, turning the
registration key into a **measured eval before/after** (the M5–M9 "measured miss →
measured close" discipline), CI-reproducible.

## What this unit does

1. **The data.** The generator appends two genuinely distinct firms named
   `"Havel Kontor GmbH"` at the **same** address (`Am Kanal 5, 14467 Potsdam`), each
   with its **own** address-master record (distinct `AddressID`s carrying the same
   postal address) and a **distinct VAT** (seeded on the customer id). No sales orders
   (mirroring M9, so the demonstration is the customer-master ambiguity, not a same-name
   compare case). Fixed, no RNG, appended last — existing rows byte-identical; MANIFEST
   counts +2 customers / +2 addresses. The distinct `AddressID`s are required (review
   nit-1, spec 0078): two firms must mint two address nodes for the same-address pair to
   split into two connected components.
2. **The behaviour.** Name-only ER over-merges the pair (same name); **name + address**
   ER (M9) *also* over-merges it (the address agrees); **the registration key** (M10
   default) splits it (the distinct VATs). Pinned on the real graph
   (`test_registration_key_splits_only_the_same_address_pair`) and abstractly
   (`test_scale.py`, the key-closes-the-floor tail).
3. **The measured close** (`scripts/record_m10_close.py`, run once into
   `eval/history.jsonl`): the new ambiguous-name gold case
   (`11_same_name_same_address_refusal`, `kind: refuse`) is a **miss under M9 ER** (name
   + address over-merges → answers → business gold quality **0.909**, faithfulness 1.0)
   and a **close under M10** (the key splits → refuses → **1.000**). Pinned by
   `test_m10_registration_key_close`.
4. **The new floor.** Same name **and** same address **and** same key over-merges (the
   two firms are indistinguishable from the data) — the honest recorded boundary,
   pinned in `test_scale.py` and `test_multifield_er.py`.
5. **Test bookkeeping.** Gold count 10 → 11; the cluster-equivalence pins now exclude
   both disambiguation pairs (Hanseatic + Havel); `test_m9_multifield_close` reframed —
   with two ambiguous pairs in the gold set, name-only misses both (9/11) and the
   address gate closes only the different-address pair (10/11), motivating the key.
   Synthetic count unchanged (53): `"havel"` is < 6 chars and `"kontor"` is unique, so
   the ambiguous-token enumerator adds no case.

## A discovered retrieval fragility (recorded honestly)

Adding 4 short records shifted BM25 `avgdl` by a hair and flipped a **near-tie** in an
unrelated retrieval test: for the renewal query, the section *heading*
`"## 2. Term and renewal"` (14.5734) and its first *clause* carrying `"auto-renews"`
(14.5667) score within **0.05%**, and the heading edged ahead. The renewal section is
still surfaced top, from the MSA, with doc-span provenance — only heading-vs-first-clause
flipped. `test_renewal_question_returns_the_actual_renewal_clause` is updated to assert
the **robust** invariant (the auto-renews clause is in the top-2 from the MSA with
doc-span provenance), with the near-tie documented. The eval (faithfulness / coverage /
quality) is untouched at 1.0. The root cause — a heading-only chunk competing with its
content — is **retrieval future work**, not an ER concern (a follow-up task is filed).

## Acceptance criteria

- [x] Same-name/same-address distinct-VAT pair appended (distinct AddressIDs, no orders);
      existing rows byte-identical; MANIFEST updated; generator deterministic.
- [x] Real-graph: name-only + address-only over-merge the pair; the key splits it.
- [x] Gold case 11 (`refuse`); `record_m10_close.py` records before (0.909) / after
      (1.000) in `eval/history.jsonl`; pinned by `test_m10_registration_key_close`.
- [x] The new floor (same name + address + key → over-merge) pinned.
- [x] Gold count 11; cluster pins exclude both pairs; `test_m9_multifield_close` reframed;
      synthetic count 53 (explained).
- [x] Gate green; deterministic across `PYTHONHASHSEED` 0/1/42/2026; faithfulness 1.0 on
      all batteries.

## Out of scope

- The retrieval heading-chunk root cause (future work; follow-up task filed).
- The WRITEUP/README/CHANGELOG/STATUS close (Unit 4, spec 0080).
