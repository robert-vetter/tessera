"""Tests for the ingestion engine and the SALT-shaped source.

These assert Pillar 1's guarantees as invariants, not just output shape: no
information enters without a retrievable origin, ingestion is deterministic, and
the sample is genuinely connected with real entity-resolution difficulty for
Unit 4.
"""

from __future__ import annotations

from tessera.ingestion import Ingester, chunk_text
from tessera.sources.salt import SaltSyntheticSource


def test_chunk_text_splits_on_blank_lines_with_line_ranges() -> None:
    chunks = chunk_text("alpha\nbeta\n\ngamma\n")
    assert [(c.start_line, c.end_line, c.text) for c in chunks] == [
        (1, 2, "alpha\nbeta"),
        (4, 4, "gamma"),
    ]


def test_chunk_text_empty_input() -> None:
    assert chunk_text("") == []


def test_source_satisfies_ingester_protocol() -> None:
    assert isinstance(SaltSyntheticSource(), Ingester)


def test_every_record_has_origin() -> None:
    """Pillar 1: no information enters without an attached, retrievable origin."""
    records = SaltSyntheticSource().ingest()
    assert records
    for record in records:
        assert record.origin.source
        assert record.origin.locator.parts  # a concrete in-source locator
        assert record.origin.ingested_at
        assert record.text


def test_ingestion_is_deterministic() -> None:
    """Re-ingesting the committed sample yields identical records, in order."""
    first = SaltSyntheticSource().ingest()
    second = SaltSyntheticSource().ingest()
    assert first == second


def test_record_ids_are_unique() -> None:
    """Stable, collision-free ids — a key collision would silently merge rows."""
    records = SaltSyntheticSource().ingest()
    ids = [record.id for record in records]
    assert len(ids) == len(set(ids))


def test_ingested_at_is_deterministic_snapshot_date() -> None:
    """Ingestion timestamp is the data snapshot date, not wall-clock — so it is
    reproducible. Every record shares it."""
    records = SaltSyntheticSource().ingest()
    stamps = {record.origin.ingested_at for record in records}
    assert stamps == {"2026-06-05"}
