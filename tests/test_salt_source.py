"""Tests for the synthetic SALT-shaped dataset: connectedness, ER difficulty,
and that the demo answer traces to genuinely ingested rows.
"""

from __future__ import annotations

import re

from tessera.business.knowledge import DEMO_KB, DEMO_QUESTION
from tessera.ingestion import read_csv_rows
from tessera.retrieval import answer
from tessera.sources.salt import DATA_DIR


def _rows(name: str) -> list[dict[str, str]]:
    return list(read_csv_rows(DATA_DIR / name))


def _normalize(name: str) -> str:
    """Fold a company name to a comparison key (lowercase, umlaut-fold, alnum)."""
    folded = (
        name.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return re.sub(r"[^a-z0-9]", "", folded)


def test_sample_is_connected() -> None:
    """Referential integrity holds, so the tables still join end-to-end."""
    customers = _rows("I_Customer.csv")
    addresses = _rows("I_AddrOrgNamePostalAddress.csv")
    docs = _rows("I_SalesDocument.csv")
    items = _rows("I_SalesDocumentItem.csv")

    customer_ids = {c["Customer"] for c in customers}
    address_ids = {a["AddressID"] for a in addresses}
    doc_ids = {d["SalesDocument"] for d in docs}

    # Every customer points at a real address.
    assert all(c["AddressID"] in address_ids for c in customers)
    # Every sales document's sold-to party is a real customer.
    assert all(d["SoldToParty"] in customer_ids for d in docs)
    # Every line item belongs to a real sales document.
    assert all(i["SalesDocument"] in doc_ids for i in items)


def test_entity_resolution_difficulty_is_present() -> None:
    """The same real entity must appear under differing forms — genuine ER work,
    not a planted-easy match. Without this, Unit 4 would be measuring nothing."""
    customers = _rows("I_Customer.csv")
    addresses = _rows("I_AddrOrgNamePostalAddress.csv")

    # 1) The spotlight customer and its address master disagree on the name.
    spotlight = next(c for c in customers if c["Customer"] == "0010000007")
    spot_addr = next(a for a in addresses if a["AddressID"] == spotlight["AddressID"])
    assert spotlight["CustomerName"] != spot_addr["OrganizationName"]
    assert _normalize(spotlight["CustomerName"]) == _normalize("Mueller Logistik GmbH")

    # 2) At least one real entity appears as duplicate customers with DIFFERENT
    #    raw spellings (same normalized key, distinct surface forms).
    clusters: dict[str, set[str]] = {}
    for c in customers:
        clusters.setdefault(_normalize(c["CustomerName"]), set()).add(c["CustomerName"])
    assert any(len(forms) >= 2 for forms in clusters.values())


def test_demo_answer_traces_to_ingested_salt_rows() -> None:
    """A question about the spotlight customer's orders retrieves ingested SALT
    rows, each carrying provenance back to its source row."""
    result = answer("What are Müller Logistik's sales orders?", DEMO_KB)
    assert result.is_grounded

    support = [rec for claim in result.claims for rec in claim.support]
    salt = [rec for rec in support if rec.origin.source.startswith("salt_synthetic/")]
    assert salt  # structured rows were surfaced
    assert any("Müller Logistik GmbH" in rec.text for rec in salt)
    assert all(rec.origin.locator.kind == "table-row" for rec in salt)


def test_demo_kb_question_is_answerable() -> None:
    result = answer(DEMO_QUESTION, DEMO_KB)
    assert result.is_grounded
    assert result.claims
