"""Ingest the REAL SAP SALT dataset (a bounded slice) and ground answers on it.

The S1 real-data path (spec 0130). Where :mod:`tessera.sources.salt` ingests
the *synthetic* SALT-shaped corpus (which carries invented organization names
to exercise entity resolution), this module ingests the **actual** gated SALT
dataset — which is **fully anonymized**: customers, addresses, and sales
documents are numeric codes with **no name/description/street text anywhere**,
linked only by exact foreign key. So there is nothing for name-similarity
entity resolution to resolve; what real SALT supports, and what this delivers,
is **deterministic FK-linked grounding with claim-level provenance** over the
real records. (The finding is written up in ``docs/SALT_REAL.md``.)

It reads the CSV slice produced by ``scripts/salt_real_slice.py`` with the
**stdlib** (no pyarrow; that is the slice script's opt-in ``salt`` extra), so
this ingester and its tests run key-free and gated-data-free against the
committed fixture in ``data/salt_real_fixture/``. The engine
(:mod:`tessera.graph`, :mod:`tessera.grounding`) is reused unchanged; nothing
real is committed (the slice lives under gitignored ``var/``).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tessera.connect.scrub import neutralize_controls
from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import (
    REFUSAL_MESSAGE,
    Answer,
    Claim,
    EvidenceRecord,
    Locator,
    Origin,
)

# The slice's four CSV files and their natural-key columns. The shape is
# documented in docs/SALT_REAL.md; the committed fixture matches it exactly.
_INGESTED_AT = "2026-07-04"  # the SALT snapshot date is not per-row; fixed + honest


def _clean(value: str) -> str:
    """Neutralize control characters on every ingested field (foreign real
    input, the M18 connect precedent), leaving legitimate content intact."""
    cleaned, _ = neutralize_controls(value)
    return cleaned.strip()


def _rows(path: Path, required: frozenset[str]) -> list[dict[str, str]]:
    """Read one slice CSV, validating its header first: a hand-edited or
    schema-drifted slice fails with the file and columns NAMED, not with a
    bare ``KeyError`` three frames deep (review finding)."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                f"{path}: missing required column(s) {sorted(missing)} — "
                "expected the salt_real_slice.py schema (docs/SALT_REAL.md)"
            )
        return [{key: _clean(value) for key, value in row.items()} for row in reader]


def _record(
    source: str, table: str, row_no: int, text: str, ident: str
) -> EvidenceRecord:
    return EvidenceRecord(
        id=ident,
        origin=Origin(
            source=f"salt_real/{source}",
            locator=Locator.table_row(table, row_no),
            ingested_at=_INGESTED_AT,
        ),
        text=text,
    )


@dataclass(frozen=True)
class SaltRealSlice:
    """The ingested real-SALT slice: records + the FK-linked graph."""

    graph: KnowledgeGraph
    records: tuple[EvidenceRecord, ...]


def _address_text(row: dict[str, str]) -> str:
    parts = [f"Address {row['ADDRESSID']}: country {row['COUNTRY'] or 'unknown'}"]
    if row.get("REGION"):
        parts.append(f"region {row['REGION']}")
    return ", ".join(parts) + "."


def _doc_text(row: dict[str, str]) -> str:
    return (
        f"Sales document {row['SALESDOCUMENT']}: type {row['SALESDOCUMENTTYPE']}, "
        f"currency {row['TRANSACTIONCURRENCY']}, "
        f"incoterms {row['INCOTERMSCLASSIFICATION']}, "
        f"created {row['CREATIONDATE']}."
    )


def ingest_slice(slice_dir: str | Path) -> SaltRealSlice:
    """Ingest the CSV slice at ``slice_dir`` into records + an FK graph.

    Nodes: ``Customer:<code>``, ``Address:<id>``, ``SalesDoc:<id>``,
    ``SalesItem:<doc>/<item>``. Edges (exact foreign keys, the only linkage
    real SALT offers): ``located_at`` (customer→address), ``sold_to``
    (item→customer), ``line_of`` (item→document).
    """
    base = Path(slice_dir)
    graph = KnowledgeGraph()
    records: list[EvidenceRecord] = []

    def add(node_id: str, kind: str, record: EvidenceRecord) -> None:
        records.append(record)
        graph.add_node(Node(record=record, kind=kind))

    for index, row in enumerate(
        _rows(base / "addresses.csv", frozenset({"ADDRESSID", "COUNTRY", "REGION"})),
        start=1,
    ):
        add(
            f"Address:{row['ADDRESSID']}",
            "Address",
            _record(
                "addresses.csv",
                "I_AddrOrgNamePostalAddress",
                index,
                _address_text(row),
                f"Address:{row['ADDRESSID']}",
            ),
        )
    for index, row in enumerate(
        _rows(base / "customers.csv", frozenset({"CUSTOMER", "ADDRESSID"})), start=1
    ):
        code = row["CUSTOMER"]
        add(
            f"Customer:{code}",
            "Customer",
            _record(
                "customers.csv",
                "I_Customer",
                index,
                f"Customer {code} (address {row['ADDRESSID']}).",
                f"Customer:{code}",
            ),
        )
        graph.add_edge(
            Edge(
                src=f"Customer:{code}",
                dst=f"Address:{row['ADDRESSID']}",
                relation="located_at",
            )
        )
    for index, row in enumerate(
        _rows(
            base / "sales_docs.csv",
            frozenset(
                {
                    "SALESDOCUMENT",
                    "TRANSACTIONCURRENCY",
                    "SALESDOCUMENTTYPE",
                    "INCOTERMSCLASSIFICATION",
                    "CREATIONDATE",
                }
            ),
        ),
        start=1,
    ):
        add(
            f"SalesDoc:{row['SALESDOCUMENT']}",
            "SalesDoc",
            _record(
                "sales_docs.csv",
                "I_SalesDocument",
                index,
                _doc_text(row),
                f"SalesDoc:{row['SALESDOCUMENT']}",
            ),
        )
    for index, row in enumerate(
        _rows(
            base / "sales_items.csv",
            frozenset({"SALESDOCUMENT", "SALESDOCUMENTITEM", "SOLDTOPARTY", "PRODUCT"}),
        ),
        start=1,
    ):
        item_id = f"SalesItem:{row['SALESDOCUMENT']}/{row['SALESDOCUMENTITEM']}"
        add(
            item_id,
            "SalesItem",
            _record(
                "sales_items.csv",
                "I_SalesDocumentItem",
                index,
                f"Sales document {row['SALESDOCUMENT']} item "
                f"{row['SALESDOCUMENTITEM']}: product {row['PRODUCT']}, "
                f"sold to {row['SOLDTOPARTY']}.",
                item_id,
            ),
        )
        graph.add_edge(
            Edge(src=item_id, dst=f"Customer:{row['SOLDTOPARTY']}", relation="sold_to")
        )
        graph.add_edge(
            Edge(
                src=item_id, dst=f"SalesDoc:{row['SALESDOCUMENT']}", relation="line_of"
            )
        )

    return SaltRealSlice(graph=graph, records=tuple(records))


def describe_customer(customer_code: str, data: SaltRealSlice) -> Answer:
    """Ground "what do we know about customer <code>?" over the real slice.

    Composes, each claim citing a real SALT row: the customer record, its
    address (via ``located_at``), and its sales documents (via ``sold_to`` →
    ``line_of``). Refuses on an unknown code — no evidence, no claim. No
    name-ER (real SALT has no names); pure FK traversal.
    """
    question = f"What do we know about customer {customer_code}?"
    graph = data.graph
    node_id = f"Customer:{customer_code}"
    try:
        customer = graph.node(node_id)
    except KeyError:
        return Answer(
            question=question,
            claims=(),
            refusal=f"No customer {customer_code} in the SALT slice. {REFUSAL_MESSAGE}",
        )

    claims: list[Claim] = [Claim(text=customer.record.text, support=(customer.record,))]

    for address_id in sorted(_dst(graph, node_id, "located_at")):
        address = graph.node(address_id)
        claims.append(Claim(text=address.record.text, support=(address.record,)))

    # The customer's sales documents: items sold to it, then their headers.
    item_ids = sorted(_src(graph, node_id, "sold_to"))
    doc_ids = sorted({d for item in item_ids for d in _dst(graph, item, "line_of")})
    for doc_id in doc_ids:
        doc = graph.node(doc_id)
        claims.append(Claim(text=doc.record.text, support=(doc.record,)))

    return Answer(question=question, claims=tuple(claims), refusal=None)


def _dst(graph: KnowledgeGraph, src: str, relation: str) -> list[str]:
    return [e.dst for e in graph.edges if e.src == src and e.relation == relation]


def _src(graph: KnowledgeGraph, dst: str, relation: str) -> list[str]:
    return [e.src for e in graph.edges if e.dst == dst and e.relation == relation]


def customer_codes(data: SaltRealSlice) -> Iterable[str]:
    """The customer codes present in the slice (sorted, for the report)."""
    return sorted(
        node.id.removeprefix("Customer:")
        for node in data.graph.nodes
        if node.kind == "Customer"
    )
