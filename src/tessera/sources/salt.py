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
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.ingestion import read_csv_rows

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "salt_synthetic"

# The corroborating identity fields multi-field ER compares beyond the name, ordered
# by decisiveness — postal code (the stable key) before city (spec 0074 / ADR 0019).
# The knowledge of *which* attributes are an address lives here, in the source; the
# engine stays general and compares whatever fields it is handed.
ADDRESS_MATCH_FIELDS = ("postal_code", "city_name")

# The full corroborating signal for the business vertical (Milestone 10, spec 0078 /
# ADR 0020). The VAT registration number is an **exact legal-entity identity key**, so
# it leads the ordered tuple — a registration-key match/mismatch decides above the
# (fuzzy, postal-anchored) address, closing the one residual address-only ER cannot
# reach: two distinct firms with the SAME name AND the SAME address. ``match_fields``
# being ordered by decisiveness (``resolution.compare_match_fields``), the address is
# consulted only when a customer carries no key.
CUSTOMER_MATCH_FIELDS = ("vat_registration",) + ADDRESS_MATCH_FIELDS


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

    def node_attributes(self) -> dict[str, tuple[tuple[str, str], ...]]:
        """Structured facts to attach to nodes. Schema knowledge stays here:

        - each **sales document's** net amount and currency, so the graph can
          aggregate without parsing rendered text;
        - each name-bearing node's **address signature** (``postal_code`` +
          ``city_name``) for multi-field ER (spec 0074 / ADR 0019) — on the address
          node (its own row) and, denormalized via ``AddressID``, on the customer node;
        - each name-bearing node's **registration key** (``vat_registration``) for
          registration-key ER (spec 0078 / ADR 0020) — the exact legal-entity identity
          key. It lives on the customer master (``I_Customer.VATRegistration``) and is
          **denormalized onto the customer's linked address node** (via ``AddressID``),
          so the SAME key is on BOTH nodes a same-name/same-address pair would otherwise
          bridge through — required for the two firms to split into two connected
          components. A *shared* (serviced-office) address — one referenced by more than
          one customer — carries no single firm's key and is left without one (absence
          falls back to name + postal; it is never a contradiction).

        Together (``CUSTOMER_MATCH_FIELDS``) these let
        :meth:`~tessera.graph.KnowledgeGraph.resolve_entities` corroborate a name match
        with the key first, then the address.
        """
        attrs: dict[str, tuple[tuple[str, str], ...]] = {}
        for row in read_csv_rows(self.data_dir / "I_SalesDocument.csv"):
            attrs[f"I_SalesDocument:{row['SalesDocument']}"] = (
                ("net_amount", row["TotalNetAmount"]),
                ("currency", row["TransactionCurrency"]),
            )
        address_signature: dict[str, tuple[tuple[str, str], ...]] = {}
        for row in read_csv_rows(self.data_dir / "I_AddrOrgNamePostalAddress.csv"):
            address_signature[row["AddressID"]] = (
                ("postal_code", row["PostalCode"]),
                ("city_name", row["CityName"]),
            )
        customer_rows = list(read_csv_rows(self.data_dir / "I_Customer.csv"))
        # Denormalize each customer's key onto its address node — but ONLY when the
        # address belongs to a single customer. A shared (serviced-office) address
        # carries no single firm's key, so it is left without one: absence is never a
        # contradiction (it falls back to name + postal), where denormalizing one of
        # several firms' keys onto it would be wrong. On this 1:1 corpus every address
        # has one customer, so this is a no-op; it keeps the source correct for a real
        # SALT extract where addresses can be shared.
        address_refs = Counter(r["AddressID"] for r in customer_rows)
        vat_by_address = {
            r["AddressID"]: r.get("VATRegistration", "")
            for r in customer_rows
            if address_refs[r["AddressID"]] == 1
        }
        for address_id, signature in address_signature.items():
            vat = vat_by_address.get(address_id)
            attrs[f"I_AddrOrgNamePostalAddress:{address_id}"] = signature + (
                (("vat_registration", vat),) if vat else ()
            )
        for row in customer_rows:
            signature = address_signature.get(row["AddressID"], ())
            vat = row.get("VATRegistration", "")
            combined = signature + ((("vat_registration", vat),) if vat else ())
            if combined:
                attrs[f"I_Customer:{row['Customer']}"] = combined
        return attrs

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
