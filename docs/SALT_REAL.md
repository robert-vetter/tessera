# Running on the real SAP SALT dataset (S1)

Since Phase 1, Tessera has run on **synthetic** data built on SALT's *schema*,
with the real dataset a documented drop-in "gated only by Hugging Face access"
([`data/salt_synthetic/NOTICE`](https://github.com/robert-vetter/tessera/blob/main/data/salt_synthetic/NOTICE)).
That access came through on 2026-07-04. This report records what the real
dataset actually is, what Tessera does on it, and — honestly — what it cannot.

Spec: [`specs/0130`](https://github.com/robert-vetter/tessera/blob/main/specs/0130-salt-real-data-evaluation.md).
No real SALT data is committed (it is gated; redistribution is unclear — the
`NOTICE` rule); the slice lives under gitignored `var/`. Everything below is
reproducible by anyone with gated access via the two commands in
[§ Reproduce](#reproduce).

## The finding: real SALT is fully anonymized — the difficulty is relational, not lexical

Inspecting the eight parquet tables (`var/salt_real/`, ~4.6M rows) yields one
load-bearing fact:

- **`I_Customer`** is `(CUSTOMER, ADDRESSID)` — a numeric code and an address
  id. **No name.** Example: customer `0000109997`.
- **`I_AddrOrgNamePostalAddress`** — despite the name — has an
  `ADDRESSREPRESENTATIONCODE` that is empty on **0 of 1,788,887** rows; the
  only content is `COUNTRY` (ISO code) and a ~20%-filled `REGION`. **No
  organization name, street, or city.**
- Across **all eight tables** there is **no free-text name / description /
  street / city column** — the only "name-ish" columns (`SALESORGANIZATION`,
  `ORGANIZATIONDIVISION`) are numeric codes. Every entity is a code; linkage
  is by **exact foreign key**.

This confirms, on the real data, the SALT-KG thesis that
[MARKET §7](MARKET.md) cites from SAP's own researchers — models show "gaps
in [their] ability to leverage semantics in relational context." **SALT's
difficulty is relational, not lexical.**

**What this means for Tessera, recorded rather than hidden:** the project's
name-similarity entity resolution
([ADR 0004](adr/0004-graph-and-entity-resolution.md) and the multi-field
refinements) has *nothing to bite on* in real SALT — the
"Müller / Mueller / GmbH-variant" resolution is a capability the **synthetic**
corpus was deliberately built to exercise (it *invented* the names); it has no
real-SALT analog. That is not a gap in SALT and not a defect in Tessera — it
is the honest shape of the data. What real SALT supports, and what Tessera
delivers here, is the **structural half** of the engine: deterministic,
FK-linked grounding with claim-level provenance over the actual records.

## What Tessera does on it

`tessera/sources/salt_real.py` ingests a bounded, connected slice into the
**unchanged** engine graph: `Customer`, `Address`, `SalesDoc`, and `SalesItem`
nodes, linked by the exact foreign keys that are the only linkage real SALT
offers — `located_at` (customer → address), `sold_to` (item → customer),
`line_of` (item → document). A grounded answer for "what do we know about
customer `<code>`?" composes the customer row, its address, and its sales
documents — **every claim citing a real SALT row**, no invented names, an
unknown code refused.

## The recorded run (2026-07-04)

A deterministic slice of **25 real customers** that appear as `SOLDTOPARTY`
and have a resolvable address (13,155 such customers exist), with exactly
their addresses, sales-document headers, and line items:

```
slice: 25 customers · 25 addresses · 59 sales documents · 115 line items
       (224 evidence records, 255 FK edges)
faithfulness: 109 / 109 emitted claims verifier-supported = 1.000
              (scored by the eval's own is_supported — eval/metrics.py)
provenance:   0 dangling citations — every claim traces to a real slice row
```

A real grounded answer, verbatim (customer `0001114321`, a Romanian customer
trading in EUR and RON):

```
Q: What do we know about customer 0001114321?

- Customer 0001114321 (address 3001525443).
    ↳ salt_real/customers.csv (table I_Customer, row 1)
- Address 3001525443: country RO.
    ↳ salt_real/addresses.csv (table I_AddrOrgNamePostalAddress, row 25)
- Sales document 0002414945: type ZMUN, currency EUR, incoterms FCA, created 2020-04-06.
    ↳ salt_real/sales_docs.csv (table I_SalesDocument, row 53)
- Sales document 0002414950: type ZMUN, currency RON, incoterms FCA, created 2020-04-06.
    ↳ salt_real/sales_docs.csv (table I_SalesDocument, row 54)
- Sales document 0002415390: type ZMUN, currency EUR, incoterms DAP, created 2020-04-06.
    ↳ salt_real/sales_docs.csv (table I_SalesDocument, row 55)
```

Every line is a real SALT record with a provenance path back to the exact
table row. This is grounded, provenance-complete answering **on the actual
gated SAP dataset** — "ran on real SALT", scoped to what real SALT is.

## Honest limits

- **Anonymized → no name-ER.** The headline finding: entity resolution over
  names has no real-SALT analog. Tessera's ER capability is exercised on the
  synthetic corpus and on the DevEx/GitHub verticals, not here. Real SALT
  linkage is exact-key, and that is what this path uses.
- **Bounded slice, not the full 4.6M rows.** The in-process graph is a
  demo-scale structure; the slice (25 customers) is a genuine connected
  subgraph, enough to prove grounding on real data. Ingesting all 139,611
  customers is named future work (a real-scale test), not this unit.
- **No real data committed, so no committed battery.** The gated data and its
  slice stay under `var/`; the CI floor is `tests/test_salt_real.py` over an
  authored anonymized fixture (`data/salt_real_fixture/`, real schema, no
  names). This report is the proof of the real run — the same posture as the
  BYO connector's recorded proofs ([PILOT.md](PILOT.md)).
- **Faithfulness here is structural containment**, as everywhere in Tessera:
  each claim is a verbatim row snippet, so 1.000 means every claim is backed
  by exactly its cited record — not a semantic judgment.

## Reproduce

With gated Hugging Face access to
[`SAP/SALT`](https://huggingface.co/datasets/SAP/SALT) and an `HF_TOKEN`:

```bash
# 1) pull the gated dataset into gitignored var/ (once, ~116 MB)
uvx --from huggingface_hub hf download SAP/SALT --repo-type dataset \
    --local-dir var/salt_real --token "$HF_TOKEN"

# 2) extract the deterministic slice, then ground on it
uv sync --extra salt
uv run python scripts/salt_real_slice.py         # → var/salt_real_slice/
uv run python -c "from tessera.sources.salt_real import ingest_slice, describe_customer, customer_codes; \
d = ingest_slice('var/salt_real_slice'); \
print(describe_customer(next(iter(customer_codes(d))), d).render())"
```

The ingester and its tests need neither `pyarrow` nor the gated data
(`uv run pytest tests/test_salt_real.py`); only the one-time slice extraction
does.
