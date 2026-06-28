# 0077. Milestone 10 plan: registration/tax-key entity resolution

- **Phase / milestone:** Milestone 10 — Registration/tax-key entity resolution:
  close the one ER floor that name + address ER leaves — two genuinely distinct
  firms with the *same* name **and** the *same* address, which only an exact
  identity key separates (post-roadmap; ROADMAP phases complete and tagged
  `phase-0`…`phase-4`; hardening `milestone-5`; embeddings-on-SAP `milestone-6`;
  embeddings-beyond-retrieval `milestone-7`; deterministic-ER-precision
  `milestone-8`; multi-field name+address ER `milestone-9`)
- **Issue:** —
- **Status:** approved (autonomous mode, per spec 0018: decisions recorded here
  instead of asked — except the two project-shaping scope questions below, which
  were asked and answered 2026-06-28)

## Problem

Milestone 9 added multi-field ER (name + address, ADR 0019), closing the three
Milestone-8 residuals with a second deterministic signal — the address — folded
into the name decision by a two-way gate. It left **one** floor, recorded in the
M9 close, in ADR 0019's "remaining floor", and pinned by a test
(`tests/test_scale.py::test_character_identical_firms_split_by_address`, third
assertion):

> Two genuinely distinct firms carrying the **same** name **and** the **same**
> address. Address agreement (the strongest M9 signal) corroborates a merge, so
> the firms over-merge. Only an exact identity key — a registration / tax number —
> tells them apart.

This is the recorded **M9 next lever** (the M9 STATUS "next milestone", ADR 0019's
consequences + alternatives, ADR 0004's `future work`). ADR 0004 already named it:
*"real master-data ER matches on multiple fields (name **and** address, etc.)"* and
ADR 0019's alternative *"a registration/tax key as the disambiguator … the cleanest
exact key, and a real SALT field … named as a possible later field for the residual
same-name/same-address case."* M10 takes it.

Like Milestones 8–9 — and unlike Milestones 6–7 — this is **deterministic, offline,
and fully CI-reproducible**: no embedding, no cloud, no online run. The
claim/faithfulness path stays embedding-free; the leak-guard is untouched.

**Maintainer decisions (asked 2026-06-28, because they shape the dataset):**

1. **Data population — VATRegistration on every customer, per legal entity.** Real
   master data carries a registration key on every firm, so the synthetic
   `I_Customer` master gets a `VATRegistration` column populated for **all**
   customers, assigned **per canonical entity** (duplicates of one firm share it;
   distinct firms differ). The realistic choice over a column populated for only
   the two demonstration firms; its cost — that every business ER decision now
   names the *key* rather than the postal as the deciding field — is honest (the
   key is the stronger signal) and the **resolved cluster signatures stay
   byte-identical** (proven, not assumed).
2. **Key field — `VATRegistration`.** The EU VAT registration number (e.g.
   `DE123456789`), a real S/4HANA `I_Customer` field and a globally recognised
   exact legal-entity identity key. (Rejected: `TaxNumber1`; an invented
   company-registration column — see ADR 0020.)

## The design (the one technical finding, recorded for ADR 0020)

**The Milestone-9 engine already supports this — with no engine change.** The
maintainer's framing offered "a decisive third `match_field` above postal" *or* "a
separate stronger signal". It is cleanly the first, and `resolution.py` /`graph.py`
already implement exactly the mechanism it needs:

- `compare_match_fields` is already **ordered by decisiveness, first field present
  on both decides, exact normalized equality** (`DEFAULT_FIELD_MATCH_THRESHOLD =
  1.0`). A registration key *is* an exact-equality field — it slots in as the
  **first** entry of `match_fields`, ahead of postal.
- The two-way gate (`graph._merge_reason`) already does the right thing for any
  field: a **CONTRADICT** vetoes a name-merge (same name + same address + different
  key → *split*, the M10 floor) and an **AGREE** on a name-vetoed pair bridges.

So Milestone 10 touches **only** the business source (`sources/salt.py` — the
additive `vat_registration` attribute + the `match_fields` ordering, the sanctioned
source delta from ADR 0019/0011), the synthetic data, the eval (a gold case +
recorded before/after), and tests. **`graph.py` and `resolution.py` stay
empty-diff** — the first ER milestone since M7 that leaves the engine untouched.

Two implementation points fall out of the connected-components model:

- **The key is denormalized onto the address node, exactly as postal/city are.**
  Resolution candidates are *all* name-bearing nodes — customer **and** address
  nodes. For the same-name/same-address pair to split into two connected
  components, *every* cross-firm pair (customer↔customer, address↔address,
  customer↔address) must veto — so the key must be present on the address node too.
  The source already denormalizes the address signature onto the customer via
  `AddressID`; M10 denormalizes the *customer's* key onto its address node by the
  same join. Verified on the 4-node case: with the key on both, the two firms form
  two clean components.
- **The key decides above postal — which retires M9's "postal-anchored, not
  postal-perfect" cost.** A genuine same-firm pair carrying the same key but
  *different* postals (real-world data entry) now correctly **merges** (the key is
  consulted first), where M9 would have split it on the postal disagreement. A free
  consequence of key-first ordering, demonstrated by a test and recorded honestly.

The additive/reversible model is unchanged (ADR 0004): a confirmed pair is still an
ordinary `Resolution` carrying its reason (now naming the deciding key field) and
confidence; clusters stay derived connected components; `remove_resolution`
re-splits.

## Success criterion

The last name+address floor — two distinct firms with the **same** name **and** the
**same** address — is **closed by an exact registration key**, offline and provably
in CI, with the headline landing as a measured eval close:

- The new same-name/**same-address** disambiguation pair (distinct VATs) resolves
  to **two** entities; a same-name/same-address/**same-VAT** pair (genuinely one
  firm) still **merges** (the positive control — the key is a two-way decisive
  signal, not just a splitter).
- **No correct merge is lost and no existing cluster moves.** VAT-on-all-customers
  changes the *deciding field* (postal → key) for every business merge but not the
  *outcome* — proven by a **cluster-signature byte-identical** hash over the
  business and devex graphs (the M8/M9 discipline), not assumed. devex /
  github_actions are untouched (none-path, `match_fields=()`).
- **The measured close (the headline).** The appended same-name/same-address pair
  makes the ambiguous-name gold question a **measured miss** under M9 multi-field
  ER (name + address over-merges the pair on the agreeing address, so it answers
  where a refusal is correct) and a **close** under M10 (the key splits the firms,
  so it refuses as ambiguous). Both points in `eval/history.jsonl`; the *after*
  point is CI-reproducible (unlike the M6/M7 online closes).
- **Faithfulness stays the single hard gate, structural and embedding-free.** The
  key comparison is the existing pure-stdlib `compare_match_fields` in
  `resolution.py`; the leak-guard holds; the gate only splits/bridges clusters, so
  every business verifier recomputation stays supported; the floor stays at 1.0
  across all batteries.
- **CI stays offline / deterministic / key-free** — no online run (unlike M6/M7).

## Acceptance criteria

- [ ] **VATRegistration field + source wiring + ADR 0020 (Unit 2).** The generator
      adds a `VATRegistration` column to `I_Customer` (per canonical entity, all
      customers, deterministic; existing columns byte-identical; distinct VATs for
      the same-name distinct firms — the M9 Hanseatic pair). `sources/salt.py`
      exposes `vat_registration` on the customer node and denormalizes it onto the
      address node; `match_fields` becomes `("vat_registration", "postal_code",
      "city_name")`; `build_demo_graph` default updated. The business and devex
      **resolved cluster signatures are byte-identical** to M9 (hashed, pinned);
      all three batteries read byte-identical (faithfulness 1.0). Tests pin: the
      same-VAT positive control merges, the different-VAT case splits, the
      postal-override bonus, and the reason-shift (the double-typo pair now bridges
      via the key). **ADR 0020** records the design + the new floor. **Pre-merge
      5-lens adversarial multi-agent review** (the source is in the ADR 0008 frozen
      list and VAT-first shifts every business deciding field).
- [ ] **Disambiguation pair + the measured close (Unit 3).** Two distinct
      same-named firms at the **same** address (distinct VATs) appended to the
      generator (fixed rows, RNG-stream-safe; existing rows byte-identical;
      MANIFEST counts updated; no sales orders, mirroring M9). A new business gold
      case for the ambiguous-name question (`kind: refuse`); the before (M9 name +
      address, a measured miss) and after (M10 + key, refusal restored) points
      recorded in `eval/history.jsonl` (`scripts/record_m10_close.py`); the new
      floor pinned (same name + same address + same VAT still over-merges, only an
      external registry would separate it); the `moves-only-intended-pair` and
      synthetic case-count pins updated to the new derived counts.
- [ ] **Close (Unit 4).** Gate green under multiple `PYTHONHASHSEED` values;
      WRITEUP "registration-key entity resolution" section (the floor, the
      before/after, the new boundary, the postal-override bonus); README ER section
      + numbers; CHANGELOG `[milestone-10]`; ADR nav/index; the ADR 0008 empty-diff
      core check run and the **engine confirmed empty-diff** (only `sources/salt.py`
      + data + eval changed); STATUS; tag `milestone-10`; memory; next-milestone
      kickoff handed back.

## Scope

**In — the unit breakdown (one PR each, spec each):**

| Unit | Spec | Content |
|---|---|---|
| 1 | 0077 | this plan + the two recorded scope decisions (asked 2026-06-28) |
| 2 | 0078 | `VATRegistration` column (generator, per-entity, all customers); `sources/salt.py` `vat_registration` attribute + address denormalization + `match_fields` ordering; `build_demo_graph` default; cluster-signature byte-identical pin (business + devex); the same-VAT/different-VAT/postal-override tests; reason-shift test updates; **ADR 0020**; pre-merge adversarial multi-agent review |
| 3 | 0079 | append the same-name/**same-address** distinct-VAT pair to the synthetic SALT data (RNG-safe, MANIFEST); new ambiguous-name gold case; measure & record the before/after in `eval/history.jsonl`; the new-floor pin + positive control; update the moves-only-intended-pair + synthetic case-count pins |
| 4 | 0080 | close: WRITEUP/README/CHANGELOG/STATUS, empty-diff core check (engine untouched), tag `milestone-10`, memory, kickoff |

**Out (explicitly):**

- **A separate "stronger signal" gate mechanism.** The ordered `match_field` already
  models decisiveness (key before postal); a parallel key-only code path would
  duplicate it. Recorded as a rejected alternative in ADR 0020.
- **Fuzzy key matching.** A registration key is an *exact* identity; M9 already
  proved a difflib ratio false-AGREEs on structured codes (`"D-20095"` ~ `"20095"`
  = 0.909). Exact normalized equality (the existing threshold 1.0) is correct.
- **Embeddings / the M7 regime.** `er_semantic.py` and `TESSERA_EMBEDDINGS` are
  unchanged; the key signal is deterministic and offline. No cloud, no online run.
- **Embeddings on the claim / faithfulness path.** `is_supported` stays
  deterministic and structural; ADR 0005 stays deferred.
- **A new gated eval metric for ER.** Faithfulness remains the single hard CI floor;
  ER precision/recall stays a reported measurement, not a gate.
- **Carrying the key into devex / github_actions.** They have no addresses or VATs;
  their none-path (`match_fields=()`) stays byte-identical.
- A **second real connector**; **agentic/MCP** mode; HANA graph persistence; BTP
  serving. These remain the WRITEUP's named future work.

## Eval impact

- **The measured close (headline, CI-reproducible).** The appended
  ambiguous-name gold case is a **miss under M9 multi-field ER** (name + address
  over-merges the same-address pair, so it answers where a refusal is correct → a
  quality drop, faithfulness still 1.0) and a **close under M10** (the key splits
  them → refuses → back to 1.0). Both points in `eval/history.jsonl`; the after is
  reproducible in CI, not a timestamped online point.
- **No existing number moves on the existing data.** VAT-on-all-customers changes
  the *deciding field* but not the *outcome*; the business/devex cluster signatures
  are byte-identical, *asserted by measurement*. Any number that moved without the
  new data would be a regression Unit 2 must catch.
- **Faithfulness pinned at 1.0.** Splitting an over-merge keeps every verifier
  recomputation sound; the floor is unaffected.

## Risks / open questions

- **Mis-assigning a per-entity VAT (the central regression risk).** If two
  duplicate records of one firm got *different* VATs, the key (decided first) would
  **split a genuine merge**; if two distinct firms got the *same* VAT, the recall
  arm could **bridge** them. Mitigated by assigning VAT strictly **per canonical
  entity** (one VAT per `_ENTITIES` entry; explicit distinct VATs for the
  hand-appended same-name distinct firms) and **proven** by the cluster-signature
  byte-identical pin — a slip fails the build, it does not pass silently.
- **The reason-text shift (postal → key).** With VAT on all customers and the key
  decided first, every business merge/bridge reason now names the VAT, not the
  postal — so the M9 tests that pin reason *content* (the double-typo "bridged by
  address") are updated to the key, and `test_none_path_…` stays byte-identical
  (the none-path never consults VAT). The cluster signatures (membership, hashed)
  are unchanged; only the inspectable reason string shifts, honestly (the key is
  the stronger signal).
- **Non-EU VATRegistration realism.** EU VAT IDs are country-prefixed; non-EU firms
  would in reality carry a national tax id, not an EU VAT. The synthetic generator
  populates a country-prefixed exact key for **all** customers (so the column is
  realistically non-empty per the maintainer's choice) and documents the
  simplification: the ER mechanism relies only on exact equality, so the synthetic
  format is a faithful-enough stand-in; the demonstration firms are all German and
  carry proper `DE`-format VATs.
- **The new floor (honest boundary).** Two distinct firms with the same name **and**
  the same address **and** the same VAT are genuinely indistinguishable from the
  signals in the data — the new recorded floor, separable only by an external
  registry / human adjudication (named in ADR 0020 and the WRITEUP, pinned by a
  test). M10 does not claim to solve it; it closes the *different-key* case and
  records the *same-key* case as the next boundary.
- **Synthetic case-count drift.** The new same-name pair adds a data-derived
  synthetic ambiguous-refuse case; the count pins are updated deliberately in Unit
  3, with the new count explained.
