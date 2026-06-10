"""DevEx ingestion: the second vertical comes through the same door (spec 0027).

What matters here is not just that the records parse, but that the engine's
contracts hold unchanged for a genuinely different data family: the same
`Ingester` protocol, the same `EvidenceRecord` shape, mandatory origins, and
the kind-tagged `Locator` absorbing two new span kinds (`log-span`,
`diff-hunk`) without any engine change — ADR 0002's forward-compatibility,
cashed in a third time.
"""

from __future__ import annotations

from tessera.grounding import EvidenceRecord
from tessera.ingestion import Ingester
from tessera.sources.devex import DevExSource, split_diff_hunks


def _records() -> list[EvidenceRecord]:
    return DevExSource().ingest()


def test_devex_source_is_an_ingester() -> None:
    assert isinstance(DevExSource(), Ingester)


def test_every_record_has_provenance_and_a_unique_id() -> None:
    records = _records()
    assert records, "expected the corpus to ingest"
    ids = [record.id for record in records]
    assert len(ids) == len(set(ids))
    for record in records:
        assert record.origin.source.startswith("devex_synthetic/")
        assert record.origin.ingested_at == "2026-06-10"
        assert record.source  # the readable origin line renders for every kind


def test_structured_rows_arrive_from_all_six_tables() -> None:
    kinds = {record.id.split(":", 1)[0] for record in _records()}
    assert {"Component", "Owner", "Pipeline", "Run", "Ticket", "PR"} <= kinds


def test_failing_log_chunk_carries_signature_and_section() -> None:
    """The R-1042 integration-tests chunk is the future RCA evidence: its
    text holds the error line; its locator names the job section and lines."""
    records = {record.id: record for record in _records()}
    chunks = [
        record
        for record_id, record in records.items()
        if record_id.startswith("run_R-1042:")
        and "TimeoutError: connection to payments-db timed out" in record.text
    ]
    assert len(chunks) == 1
    locator = chunks[0].origin.locator
    assert locator.kind == "log-span"
    parts = dict(locator.parts)
    assert parts["section"] == "integration-tests"
    assert "-" in parts["lines"]


def test_log_chunks_cover_header_jobs_and_result() -> None:
    sections = {
        dict(record.origin.locator.parts)["section"]
        for record in _records()
        if record.origin.locator.kind == "log-span"
        and record.id.startswith("run_R-1041:")
    }
    assert {"header", "checkout", "build", "result"} <= sections


def test_pr_201_diff_splits_into_three_self_describing_hunks() -> None:
    hunks = [r for r in _records() if r.id.startswith("PR-201.diff:")]
    assert len(hunks) == 3
    for record in hunks:
        assert record.origin.locator.kind == "diff-hunk"
        assert record.text.startswith("diff --git ")
        assert "@@" in record.text
    files = [dict(r.origin.locator.parts)["file"] for r in hunks]
    assert files[:2] == ["src/payments/db_client.py", "src/payments/db_client.py"]
    assert files[2] == "tests/payments/test_db_client.py"


def test_split_diff_hunks_line_ranges_are_one_based_and_ordered() -> None:
    text = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-old\n"
        "+new\n"
        "@@ -9,1 +9,2 @@\n"
        "+more\n"
    )
    hunks = split_diff_hunks(text)
    assert [h.start_line for h in hunks] == [4, 7]
    assert hunks[0].end_line == 6
    assert hunks[1].end_line == 8
    assert all(h.file == "x.py" for h in hunks)


def test_run_row_text_states_the_outcome() -> None:
    records = {record.id: record for record in _records()}
    assert "status failed (failing job integration-tests)" in records["Run:R-1042"].text
    assert "status passed" in records["Run:R-1041"].text
    assert "Fixes DEVEX-204" in records["PR:PR-201"].text
    assert "TimeoutError: connection to payments-db timed out" in (
        records["Ticket:DEVEX-187"].text
    )


def test_ids_are_natural_key_stable() -> None:
    """Ids derive from natural keys, not file positions — re-ingesting an
    updated corpus keeps existing handles valid (Pillar 1, incremental)."""
    first = {record.id for record in _records()}
    second = {record.id for record in _records()}
    assert first == second
    assert "Component:SVC-PAY" in first
    assert "Owner:Payments Service" in first
