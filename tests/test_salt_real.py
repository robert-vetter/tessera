"""Real-SALT ingester + FK grounding (spec 0130), tested against the committed
anonymized fixture — no gated data, no pyarrow, CI-safe.

The fixture (`data/salt_real_fixture/`) is authored in the real SALT slice
schema (coded ids, COUNTRY/REGION, sales-doc codes; NO names, exactly as real
SALT). The load-bearing guarantees: the FK graph links the coded entities,
grounded answers cite real slice rows and pass the eval's own verifier, an
unknown customer refuses, and foreign control characters are neutralized.
"""

from __future__ import annotations

from pathlib import Path

from tessera.eval.metrics import is_supported
from tessera.sources.salt_real import (
    customer_codes,
    describe_customer,
    ingest_slice,
)

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "salt_real_fixture"


def test_slice_ingests_into_records_and_fk_edges() -> None:
    data = ingest_slice(FIXTURE)
    kinds = {node.id: node.kind for node in data.graph.nodes}
    # 2 customers + 2 addresses + 2 docs + 3 items = 9 records.
    assert len(data.records) == 9
    assert kinds["Customer:0000000001"] == "Customer"
    assert kinds["Address:3000000001"] == "Address"
    relations = {(e.src, e.relation, e.dst) for e in data.graph.edges}
    assert ("Customer:0000000001", "located_at", "Address:3000000001") in relations
    assert (
        "SalesItem:0009000001/000010",
        "sold_to",
        "Customer:0000000001",
    ) in relations
    assert (
        "SalesItem:0009000001/000010",
        "line_of",
        "SalesDoc:0009000001",
    ) in relations


def test_grounded_answer_composes_customer_address_and_docs_with_provenance() -> None:
    data = ingest_slice(FIXTURE)
    answer = describe_customer("0000000001", data)
    assert answer.is_grounded
    rendered = answer.render()
    # The customer, its address (country DE/region BW), and its two docs.
    assert "Customer 0000000001" in rendered
    assert "country DE, region BW" in rendered
    assert "Sales document 0009000001" in rendered
    # Every claim cites a real slice row (provenance complete).
    for claim in answer.claims:
        assert claim.support
        for record in claim.support:
            assert record.origin.source.startswith("salt_real/")


def test_every_real_slice_claim_passes_the_faithfulness_verifier() -> None:
    """The eval's own verifier accepts every emitted claim (each is a verbatim
    row snippet). This is what makes the recorded real run's 1.000 honest."""
    data = ingest_slice(FIXTURE)
    nodes = {node.id: node for node in data.graph.nodes}
    for code in customer_codes(data):
        for claim in describe_customer(code, data).claims:
            assert is_supported(claim, nodes, data.graph), claim.text


def test_unknown_customer_is_refused() -> None:
    data = ingest_slice(FIXTURE)
    answer = describe_customer("9999999999", data)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "9999999999" in answer.refusal


def test_only_the_customer_s_own_documents_are_surfaced() -> None:
    """FK isolation: customer 2's answer shows its doc, never customer 1's."""
    data = ingest_slice(FIXTURE)
    rendered = describe_customer("0000000002", data).render()
    assert "Sales document 0009000002" in rendered  # its own (USD)
    assert "0009000001" not in rendered  # customer 1's, not leaked


def test_control_characters_in_foreign_fields_are_neutralized(tmp_path: Path) -> None:
    """Real ingested fields are foreign input (M18 precedent): a smuggled
    escape sequence must not survive into a claim."""
    slice_dir = tmp_path / "slice"
    slice_dir.mkdir()
    (slice_dir / "customers.csv").write_text(
        "CUSTOMER,ADDRESSID\n0000000001,3000000001\n", encoding="utf-8"
    )
    (slice_dir / "addresses.csv").write_text(
        "ADDRESSID,COUNTRY,REGION\n3000000001,D\x1b[31mE,\n", encoding="utf-8"
    )
    (slice_dir / "sales_docs.csv").write_text(
        "SALESDOCUMENT,TRANSACTIONCURRENCY,SALESDOCUMENTTYPE,"
        "INCOTERMSCLASSIFICATION,CREATIONDATE\n",
        encoding="utf-8",
    )
    (slice_dir / "sales_items.csv").write_text(
        "SALESDOCUMENT,SALESDOCUMENTITEM,SOLDTOPARTY,PRODUCT\n", encoding="utf-8"
    )
    data = ingest_slice(slice_dir)
    address = data.graph.node("Address:3000000001")
    assert "\x1b" not in address.record.text
    assert "\x1b[31m" not in address.record.text


def test_malformed_slice_fails_with_the_file_and_columns_named(
    tmp_path: Path,
) -> None:
    """A schema-drifted slice must fail diagnosably, not with a bare
    KeyError (review finding): the error names the file and the columns."""
    import pytest

    slice_dir = tmp_path / "slice"
    slice_dir.mkdir()
    # addresses.csv missing ADDRESSID entirely.
    (slice_dir / "addresses.csv").write_text("COUNTRY,REGION\nDE,\n", encoding="utf-8")
    (slice_dir / "customers.csv").write_text(
        "CUSTOMER,ADDRESSID\n0000000001,3000000001\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"addresses\.csv.*ADDRESSID"):
        ingest_slice(slice_dir)
