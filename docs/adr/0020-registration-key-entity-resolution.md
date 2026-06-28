# 0020. Registration-key entity resolution: the exact decisive field

- **Status:** accepted
- **Date:** 2026-06-28

## Context

Multi-field ER (ADR 0019) corroborated a name match with the **address**, folded
into the name decision by a two-way gate (a contradicting address vetoes an
over-merge; an agreeing address bridges a name-vetoed near-match). It closed the
three Milestone-8 residuals but left **one** floor, recorded in the M9 close, in
ADR 0019's consequences (*"the residual is now only the genuinely address-ambiguous
case — same name *and* same address but distinct firms — which a registration/tax
key, named future work, would separate"*), and pinned by
`tests/test_scale.py::test_character_identical_firms_split_by_address` (third
assertion):

> Two genuinely distinct firms carrying the **same** name **and** the **same**
> address. The address *agrees* (it is the same), so it corroborates a merge — the
> firms over-merge. Only an exact identity key — a registration / tax number — tells
> them apart.

ADR 0004's `future work` named multi-field matching including *"name **and**
address, etc."*; ADR 0019's alternatives named the key explicitly: *"a
registration/tax key as the disambiguator now … the cleanest exact key, and a real
SALT field … named as a possible later field for the residual same-name/same-address
case."* The maintainer authorised acting on it (the Milestone-10 scope questions,
answered 2026-06-28): add a `VATRegistration` field to the customer master, populated
**per legal entity on every customer**, and make the exact key the decisive
identity signal.

## Decision

**The Milestone-9 engine already supports this — the key needs no new mechanism.**
`resolution.compare_match_fields` is already *ordered by decisiveness, first field
present on both decides, exact normalized equality* (`DEFAULT_FIELD_MATCH_THRESHOLD =
1.0`), and the two-way gate (`graph._merge_reason`) already vetoes on CONTRADICT and
bridges on AGREE for **whatever** field leads `match_fields`. A registration key *is*
an exact-equality field, so it slots in as the **first** entry of the business
vertical's `match_fields`:

```
CUSTOMER_MATCH_FIELDS = ("vat_registration", "postal_code", "city_name")
```

- **The key decides above the address.** Because the comparison is "first field
  present on both decides", a registration-key match/mismatch is consulted *before*
  the (fuzzy, postal-anchored) address. Same name + same address + **different key**
  → CONTRADICT → **veto** (split — the M10 floor). Same name + same address + **same
  key** → AGREE → merge (the positive control: a genuine same firm).
- **It is denormalized onto both nodes a same-address pair bridges through.**
  Resolution candidates are *all* name-bearing nodes — customer **and** address
  nodes. For the two firms to split into two connected components, every cross-firm
  pair (customer↔customer, address↔address, customer↔address) must veto, so the key
  must be present on the address node too. The key lives on the customer master
  (`I_Customer.VATRegistration`); the source denormalizes it onto the customer's
  linked address node via `AddressID` (a 1:1 link in this corpus), exactly as the
  address signature is denormalized onto the customer. Verified on the 4-node case:
  with the key on both, the firms form two clean components; without it on the
  address node, the address↔address pair would agree on the postal and re-bridge them.
- **It retires Milestone-9's "postal-anchored, not postal-perfect" cost (a free
  consequence).** A genuine same-firm pair carrying the *same* key but *different*
  postals (real-world data entry) now correctly **merges** — the key is consulted
  first and overrides the postal disagreement, where M9 would have split it. Pinned
  by `test_registration_key_decides_above_the_address`.
- **VAT is assigned per canonical entity.** Every duplicate record of one firm shares
  one VAT (so a genuine merge is never split by the key); distinct firms differ. The
  generator seeds the VAT on the canonical entity name for the duplicate-bearing
  entities and on the unique customer id for the hand-appended firms that share a name
  but are genuinely distinct (so they get distinct keys). A hash collision between two
  distinct seeds is a **loud build failure** (`_seen`), not a silent over-merge.
- **The additive/reversible model is unchanged (ADR 0004/0019).** A confirmed pair is
  still an ordinary `Resolution` with a `reason` (now naming the deciding key field)
  and `confidence`; clusters stay derived connected components; `remove_resolution`
  re-splits. Confidence stays the name-similarity proxy (the key evidence is recorded
  in the `reason`, not fabricated into a recalibrated score — the ADR 0004 honesty).

**The one engine delta is a wording generalization, not a behavior change.** The
bridge arm of `_merge_reason` hardcoded "bridged by **address**"; under a key-led
`match_fields` the bridging field is the key, so the string would be a small
dishonesty in an inspectable provenance reason (the project's first principle).
Generalized to "bridged by **corroborating field**" — `signal.detail` already names
*which* field agreed (`vat_registration` / `postal_code`). The gate logic, the truth
table, `compare_match_fields`, and every cluster outcome are **unchanged**;
`resolution.py` is empty-diff. This is the third sanctioned engine delta after M8/M9,
the smallest of the three (a one-line honesty refinement).

**VATRegistration is a real S/4HANA field; the synthetic value is a faithful-enough
stand-in.** EU VAT IDs are country-prefixed (`DE` + 9 digits for the German
demonstration firms — the real shape). Non-EU firms would carry a national tax id
rather than an EU VAT; the generator populates a uniform country-prefixed exact key
for **every** customer (so the column is realistically non-empty, the maintainer's
choice) and documents the simplification — the ER mechanism relies only on **exact
equality**, so the format beyond "a stable exact per-firm key" does not affect
correctness.

## Consequences

- **Easier:** the last name+address floor is closed by an exact key, deterministically
  and *in CI* (no online run, unlike M6/M7) — two distinct firms with the same name
  **and** the same address split on a different key; a genuine same firm with the same
  key still merges. The recall/precision arms are both exercised by the key.
- **Non-regression, measured.** Adding a VAT to every customer and leading
  `match_fields` with it changes the *deciding field* (postal → key) but not the
  *outcome*: the resolved clusters are **byte-identical** between the VAT-first default
  and the M9 address-only path on the existing data (`test_vat_first_moves_no_cluster_
  on_existing_data`, a frozenset equality — not assumed). A mis-assigned per-entity
  VAT would split a genuine merge and fail that pin. devex / github_actions are
  untouched (none-path, `match_fields=()`).
- **The reason text shifts, honestly.** Every business merge/bridge reason now names
  the VAT (the stronger signal) rather than the postal; the M9 tests pinning reason
  *content* are updated; the none-path reason stays byte-identical (it never consults
  a field).
- **The new floor (the honest boundary).** Two distinct firms with the same name
  **and** the same address **and** the same VAT are indistinguishable from the signals
  in the data and over-merge — separable only by an external registry or human
  adjudication. M10 closes the *different-key* case and records the *same-key* case as
  the next boundary, pinned by a test (the same mechanical "merge" as the positive
  control, framed as the limitation).
- **ADR 0004's "single name-similarity threshold … transitive over-merge" cost is
  closed for the realistic master-data signals.** M8 closed the generic-suffix case;
  M9 the character-identical-different-address and two-firm-suffix cases; M10 the
  character-identical-**same-address** case. What remains is genuinely beyond the data.
- **Faithfulness stays the single hard gate, structural and embedding-free.** The key
  comparison is the existing pure-stdlib `compare_match_fields` in `resolution.py`; the
  leak-guard holds; the gate only splits/bridges clusters, so every business verifier
  recomputation stays supported; the floor stays at 1.0 across all batteries.

## Alternatives considered

- **A separate "stronger signal" code path** (a key-only gate parallel to the address
  gate). Rejected: the ordered `match_field` already models decisiveness (key before
  postal); a parallel path would duplicate the two-way gate and risk divergence. The
  key is "just another field, placed first" — the simplest correct design.
- **Fuzzy key matching** (a difflib ratio on the VAT). Rejected: a registration key is
  an *exact* identity, and M9 already proved a character ratio false-AGREEs on
  structured codes (`"D-20095"` ~ `"20095"` = 0.909). Exact normalized equality (the
  existing `threshold = 1.0`) is correct; `normalize` still folds case so `DE…`/`de…`
  agree.
- **Putting VAT on the address master CSV.** Rejected: a registration number is a
  property of the *legal entity* (the customer / business partner), not of a postal
  address (a serviced office can host several firms). It lives on `I_Customer` and is
  denormalized onto the address *node* in the source (where the schema knowledge
  lives), not added as an address column.
- **Populating VAT only for the two demonstration firms** (empty elsewhere). Rejected
  by the maintainer in favour of realism: real master data carries a key on every
  firm. The cost — every business deciding field now names the key, and the
  cluster-equivalence must be *proven* rather than trivially true — is paid by the
  byte-identical pin.
- **`TaxNumber1` or an invented company-registration column** instead of
  `VATRegistration`. `VATRegistration` is the most globally recognised exact
  legal-entity key and a real `I_Customer` field; `TaxNumber1` is equally real but
  less uniform in format; an invented Handelsregister column is less SALT-faithful.
  The maintainer chose `VATRegistration`.
- **A new gated ER metric.** Rejected (as in ADR 0018/0019): faithfulness stays the
  single hard CI floor; ER precision/recall stays a reported measurement.
