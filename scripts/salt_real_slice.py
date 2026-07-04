"""Extract a bounded, connected slice of the real SAP SALT dataset (spec 0130).

Run ONCE, by hand, by someone with gated Hugging Face access to ``SAP/SALT``
who has pulled it to ``var/salt_real/`` (see ``docs/SALT_REAL.md``):

    uv sync --extra salt
    uv run python scripts/salt_real_slice.py

It reads the gated parquet tables and writes a small CSV slice into
``var/salt_real_slice/`` (gitignored — real SALT is never committed, per
``data/salt_synthetic/NOTICE``). The slice is a genuine *connected* subgraph:
a deterministic set of real customers that actually appear as ``SOLDTOPARTY``
on sales items and have a resolvable address, plus exactly their addresses,
sales-document headers, and line items. Everything is sorted, so the slice —
and the report built from it — is byte-reproducible for anyone with access.

``pyarrow`` is the opt-in ``salt`` extra, imported only here; the ingester
(:mod:`tessera.sources.salt_real`) reads the emitted CSV with the stdlib.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

SOURCE = Path("var/salt_real")
DEST = Path("var/salt_real_slice")

# How many real customers the slice anchors on, and the per-customer item cap
# that keeps it demo-sized. Deterministic: customers are the lexicographically
# first that satisfy the connectivity + cap conditions.
CUSTOMER_COUNT = 25
MAX_ITEMS_PER_CUSTOMER = 20


def main() -> int:
    if not (SOURCE / "I_Customer.parquet").exists():
        print(f"{SOURCE}/ not found — pull the gated SAP/SALT dataset first ")
        print("(docs/SALT_REAL.md has the `hf download` command).")
        return 1

    customers = pq.read_table(
        SOURCE / "I_Customer.parquet", columns=["CUSTOMER", "ADDRESSID"]
    ).to_pydict()
    cust_addr = dict(zip(customers["CUSTOMER"], customers["ADDRESSID"], strict=True))
    address_ids = set(
        pq.read_table(
            SOURCE / "I_AddrOrgNamePostalAddress.parquet", columns=["ADDRESSID"]
        )["ADDRESSID"].to_pylist()
    )

    items = pq.read_table(
        SOURCE / "I_SalesDocumentItem_train.parquet",
        columns=["SALESDOCUMENT", "SALESDOCUMENTITEM", "SOLDTOPARTY", "PRODUCT"],
    )
    # Item counts per sold-to customer, to pick modestly-sized connected ones.
    counts = pc.value_counts(items["SOLDTOPARTY"])
    per_customer = dict(
        zip(
            counts.field("values").to_pylist(),
            counts.field("counts").to_pylist(),
            strict=True,
        )
    )
    # Connectivity universe, printed so the report's figure is reproducible
    # (review finding): sold-to customers whose address row actually resolves.
    eligible = [
        code
        for code in per_customer
        if code in cust_addr and cust_addr[code] in address_ids
    ]
    chosen = sorted(
        code for code in eligible if 1 <= per_customer[code] <= MAX_ITEMS_PER_CUSTOMER
    )[:CUSTOMER_COUNT]
    chosen_set = set(chosen)
    print(
        f"connected universe: {len(eligible):,} sold-to customers with a "
        f"resolvable address (of {len(per_customer):,} sold-to)"
    )
    print(f"chosen customers: {len(chosen)}")

    # The items sold to the chosen customers, and the docs they belong to.
    item_rows = [
        {
            "SALESDOCUMENT": doc,
            "SALESDOCUMENTITEM": line,
            "SOLDTOPARTY": sold,
            "PRODUCT": product,
        }
        for doc, line, sold, product in zip(
            items["SALESDOCUMENT"].to_pylist(),
            items["SALESDOCUMENTITEM"].to_pylist(),
            items["SOLDTOPARTY"].to_pylist(),
            items["PRODUCT"].to_pylist(),
            strict=True,
        )
        if sold in chosen_set
    ]
    item_rows.sort(
        key=lambda r: (r["SOLDTOPARTY"], r["SALESDOCUMENT"], r["SALESDOCUMENTITEM"])
    )
    doc_ids = {r["SALESDOCUMENT"] for r in item_rows}

    docs = pq.read_table(
        SOURCE / "I_SalesDocument_train.parquet",
        columns=[
            "SALESDOCUMENT",
            "TRANSACTIONCURRENCY",
            "SALESDOCUMENTTYPE",
            "INCOTERMSCLASSIFICATION",
            "CREATIONDATE",
        ],
    )
    doc_rows = sorted(
        (
            {
                "SALESDOCUMENT": row["SALESDOCUMENT"],
                "TRANSACTIONCURRENCY": row["TRANSACTIONCURRENCY"],
                "SALESDOCUMENTTYPE": row["SALESDOCUMENTTYPE"],
                "INCOTERMSCLASSIFICATION": row["INCOTERMSCLASSIFICATION"],
                "CREATIONDATE": str(row["CREATIONDATE"])[:10],
            }
            for row in docs.to_pylist()
            if row["SALESDOCUMENT"] in doc_ids
        ),
        key=lambda r: r["SALESDOCUMENT"],
    )

    addresses = pq.read_table(
        SOURCE / "I_AddrOrgNamePostalAddress.parquet",
        columns=["ADDRESSID", "COUNTRY", "REGION"],
    )
    wanted_addr = {cust_addr[c] for c in chosen}
    addr_rows = sorted(
        (
            {
                "ADDRESSID": r["ADDRESSID"],
                "COUNTRY": r["COUNTRY"],
                "REGION": r["REGION"],
            }
            for r in addresses.to_pylist()
            if r["ADDRESSID"] in wanted_addr
        ),
        key=lambda r: r["ADDRESSID"],
    )
    customer_rows = [{"CUSTOMER": c, "ADDRESSID": cust_addr[c]} for c in chosen]

    DEST.mkdir(parents=True, exist_ok=True)
    _write(DEST / "customers.csv", ["CUSTOMER", "ADDRESSID"], customer_rows)
    _write(DEST / "addresses.csv", ["ADDRESSID", "COUNTRY", "REGION"], addr_rows)
    _write(
        DEST / "sales_docs.csv",
        [
            "SALESDOCUMENT",
            "TRANSACTIONCURRENCY",
            "SALESDOCUMENTTYPE",
            "INCOTERMSCLASSIFICATION",
            "CREATIONDATE",
        ],
        doc_rows,
    )
    _write(
        DEST / "sales_items.csv",
        ["SALESDOCUMENT", "SALESDOCUMENTITEM", "SOLDTOPARTY", "PRODUCT"],
        item_rows,
    )
    print(
        f"wrote slice → {DEST}/ : {len(customer_rows)} customers, "
        f"{len(addr_rows)} addresses, {len(doc_rows)} docs, {len(item_rows)} items"
    )
    return 0


def _write(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
