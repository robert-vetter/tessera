# 0074. Wire the business graph to multi-field ER (no regression, measured)

- **Phase / milestone:** Milestone 9 — multi-field entity resolution (spec 0072)
- **Issue:** —
- **Status:** approved (autonomous mode)

## Problem

Unit 2 (spec 0073) built the engine: `resolve_entities(threshold, match_fields)`
with the two-way address gate. No vertical passes `match_fields` yet, so it is inert.
This unit **wires the business graph** to it — the source attaches the address
signature to its nodes and the graph builder opts in — and **proves, by measurement,
that it changes nothing on the existing data** (every genuine merge already agrees on
postal; no character-identical distinct firm exists yet). The synthetic
disambiguation pair and the measured before/after close come in Unit 4 (spec 0075);
this unit must be a pure no-op on the numbers.

## Acceptance criteria

- [ ] **Source attaches the address signature (`sources/salt.py`).**
      `node_attributes()` emits `postal_code` + `city_name` on **both** the address
      node (its own row) and the customer node (denormalized from its linked address
      via `AddressID`). The field-name knowledge lives here, in the source, exposed as
      `ADDRESS_MATCH_FIELDS = ("postal_code", "city_name")` (ordered by decisiveness).
- [ ] **Business graph opts in (`business/knowledge.py`).** `build_demo_graph`
      passes `match_fields=ADDRESS_MATCH_FIELDS` to `resolve_entities`, and takes an
      optional `match_fields` parameter (default `ADDRESS_MATCH_FIELDS`) so a name-only
      baseline can be built for the equivalence pin.
- [ ] **Cluster-signature byte-identical, pinned (not assumed).** A test asserts the
      business graph's resolved clusters are **identical** with and without
      `match_fields` (multi-field == name-only on the existing data), and that the
      existing demo-graph proofs (Bayerische 4-way, Müller customer↔address, distinct
      Logistik firms apart) still hold. The devex graph (name-only, no address attrs)
      is unchanged by construction.
- [ ] **All three batteries byte-identical to M8.** `tessera-eval` reproduces
      business gold 9 / synthetic 52, devex 9 / 24, github_actions 5 / 8, every number
      unchanged; faithfulness 1.0. The whole gate is green and deterministic across
      `PYTHONHASHSEED` values.

## Scope

**In:** `sources/salt.py` address-signature attributes + `ADDRESS_MATCH_FIELDS`;
`business/knowledge.py` opt-in; the cluster-equivalence pin. **Out:** the synthetic
disambiguation pair, the new gold case, and the recorded before/after (Unit 4). No
embedding, no cloud. devex/github_actions untouched.

## Eval impact

- **None.** The multi-field gate is inert on the existing demo data (the no-regression
  property is the whole point of separating this unit from Unit 4). Any number that
  moved here would be a regression the cluster-equivalence pin and the batteries must
  catch. The measured before/after lands in Unit 4.

## Risks / open questions

- **An existing genuine merge with a non-agreeing postal.** Would be wrongly split.
  The generator gives every duplicate of one firm the same canonical postal (only
  street/city *spelling* varies, which `normalize` folds), so none exists — but this
  is exactly what the cluster-equivalence pin verifies rather than assumes.
- **The corroboration arm adding a resolution edge** (the Noridc/Nordic Timbre
  double-typo pair now merges directly instead of via transitivity). This changes the
  *assertion set* but not the *clusters* (already connected), so the cluster signature
  stays identical — the pin compares clusters, not the resolution list, by design.
- **A node-attribute reader assuming customer/address nodes are attribute-free.**
  Checked: every `.attr()` reader targets the sales `net_amount`/`currency` keys;
  none reads customer/address attributes, so adding postal/city is additive and safe.
