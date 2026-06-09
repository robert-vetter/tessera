"""Ingest the synthetic, SALT-shaped business dataset into evidence records.

The data under ``data/salt_synthetic/`` is **synthetic** but uses SAP SALT's real
table/column/join structure (see ``scripts/generate_salt_synthetic.py`` and
``specs/0010``). This ingester is therefore **schema-faithful**: pointed at the
real SALT tables (same CSV shape), it would need no change — ingesting real SALT
is a documented drop-in, gated only by Hugging Face access.

It implements the :class:`tessera.ingestion.Ingester` contract, emitting one
:class:`~tessera.grounding.EvidenceRecord` per source row. Record ids are derived
from each table's natural key (not row position), so they are stable across
regenerations; the :class:`~tessera.grounding.Locator` still records the physical
row for provenance.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.ingestion import read_csv_rows

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "salt_synthetic"


def _money(value: str, currency: str) -> str:
    """Render a raw decimal amount with thousands separators for readability."""
    return f"{currency} {float(value):,.2f}"


def _customer_text(row: dict[str, str]) -> str:
    return (
        f'Customer {row["Customer"]}: "{row["CustomerName"]}" '
        f"(account group {row['CustomerAccountGroup']}, country {row['Country']}); "
        f"address {row['AddressID']}."
    )


def _address_text(row: dict[str, str]) -> str:
    return (
        f'Address {row["AddressID"]}: "{row["OrganizationName"]}", '
        f"{row['StreetName']} {row['HouseNumber']}, "
        f"{row['PostalCode']} {row['CityName']}, {row['Country']}."
    )


def _sales_doc_text(row: dict[str, str]) -> str:
    amount = _money(row["TotalNetAmount"], row["TransactionCurrency"])
    return (
        f"Sales document {row['SalesDocument']}: sold-to party {row['SoldToParty']}, "
        f"net value {amount}, dated {row['SalesDocumentDate']}."
    )


def _sales_item_text(row: dict[str, str]) -> str:
    amount = _money(row["NetAmount"], row["TransactionCurrency"])
    return (
        f"Item {row['SalesDocumentItem']} of sales document {row['SalesDocument']}: "
        f"{row['SalesDocumentItemText']} (material {row['Material']}), "
        f"quantity {row['OrderQuantity']}, net {amount}."
    )


@dataclass(frozen=True)
class _Table:
    """How to ingest one SALT table: its file, natural key, and row rendering."""

    table: str
    filename: str
    key: Callable[[dict[str, str]], str]
    text: Callable[[dict[str, str]], str]


_TABLES: tuple[_Table, ...] = (
    _Table("I_Customer", "I_Customer.csv", lambda r: r["Customer"], _customer_text),
    _Table(
        "I_AddrOrgNamePostalAddress",
        "I_AddrOrgNamePostalAddress.csv",
        lambda r: r["AddressID"],
        _address_text,
    ),
    _Table(
        "I_SalesDocument",
        "I_SalesDocument.csv",
        lambda r: r["SalesDocument"],
        _sales_doc_text,
    ),
    _Table(
        "I_SalesDocumentItem",
        "I_SalesDocumentItem.csv",
        lambda r: f"{r['SalesDocument']}-{r['SalesDocumentItem']}",
        _sales_item_text,
    ),
)


@dataclass(frozen=True)
class SaltSyntheticSource:
    """Ingester for the committed synthetic SALT-shaped dataset."""

    data_dir: Path = DATA_DIR

    def _snapshot_date(self) -> str:
        manifest = json.loads((self.data_dir / "MANIFEST.json").read_text("utf-8"))
        return str(manifest["snapshot_date"])

    def ingest(self) -> list[EvidenceRecord]:
        ingested_at = self._snapshot_date()
        records: list[EvidenceRecord] = []
        for spec in _TABLES:
            path = self.data_dir / spec.filename
            for row_number, row in enumerate(read_csv_rows(path), start=1):
                origin = Origin(
                    source=f"salt_synthetic/{spec.filename}",
                    locator=Locator.table_row(spec.table, row_number),
                    ingested_at=ingested_at,
                )
                records.append(
                    EvidenceRecord(
                        id=f"{spec.table}:{spec.key(row)}",
                        origin=origin,
                        text=spec.text(row),
                    )
                )
        return records

    def org_names(self) -> dict[str, str]:
        """Map each name-bearing record id to its organization name.

        These are the resolution candidates; the schema knowledge of *which*
        columns hold a name lives here, in the source, not in the graph engine.
        """
        names: dict[str, str] = {}
        for row in read_csv_rows(self.data_dir / "I_Customer.csv"):
            names[f"I_Customer:{row['Customer']}"] = row["CustomerName"]
        for row in read_csv_rows(self.data_dir / "I_AddrOrgNamePostalAddress.csv"):
            names[f"I_AddrOrgNamePostalAddress:{row['AddressID']}"] = row[
                "OrganizationName"
            ]
        return names

    def structural_edges(self) -> list[tuple[str, str, str]]:
        """Deterministic (src_id, dst_id, relation) edges from the foreign keys.

        Ids match the ingested record ids, so edges connect the same nodes.
        """
        edges: list[tuple[str, str, str]] = []
        for row in read_csv_rows(self.data_dir / "I_Customer.csv"):
            edges.append(
                (
                    f"I_Customer:{row['Customer']}",
                    f"I_AddrOrgNamePostalAddress:{row['AddressID']}",
                    "has_address",
                )
            )
        for row in read_csv_rows(self.data_dir / "I_SalesDocument.csv"):
            edges.append(
                (
                    f"I_SalesDocument:{row['SalesDocument']}",
                    f"I_Customer:{row['SoldToParty']}",
                    "sold_to",
                )
            )
        for row in read_csv_rows(self.data_dir / "I_SalesDocumentItem.csv"):
            doc = row["SalesDocument"]
            edges.append(
                (
                    f"I_SalesDocumentItem:{doc}-{row['SalesDocumentItem']}",
                    f"I_SalesDocument:{doc}",
                    "line_of",
                )
            )
        return edges
