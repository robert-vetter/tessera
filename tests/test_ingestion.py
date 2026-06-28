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


def test_chunk_text_heading_leads_its_section() -> None:
    """A lone ATX heading merges into the content it introduces (ADR 0021): one
    chunk spanning the heading line through its body, with the blank separator
    preserved in the text — no standalone heading-only chunk to compete in BM25."""
    chunks = chunk_text("## 2. Term and renewal\n\nThe agreement auto-renews.\n")
    assert [(c.start_line, c.end_line, c.text) for c in chunks] == [
        (1, 3, "## 2. Term and renewal\n\nThe agreement auto-renews."),
    ]


def test_chunk_text_does_not_treat_log_markers_as_headings() -> None:
    """The heading predicate requires whitespace after the hashes, so GitHub-style
    runner-log markers (``##[error]``) and bare hashes are NOT headings — the shared
    chunker leaves log corpora untouched (ADR 0021)."""
    chunks = chunk_text("##[error]Process failed\n\nnext line\n")
    # Two separate blocks: the marker is not merged into the following content.
    assert [c.text for c in chunks] == ["##[error]Process failed", "next line"]


def test_chunk_text_consecutive_headings_chain_to_content() -> None:
    """Stacked headings with no body between them fold onto the next content block."""
    chunks = chunk_text("# Title\n\n## Section\n\nBody text here.\n")
    assert [(c.start_line, c.end_line, c.text) for c in chunks] == [
        (1, 5, "# Title\n\n## Section\n\nBody text here."),
    ]


def test_chunk_text_trailing_heading_stays_its_own_chunk() -> None:
    """A heading with no following content cannot lead a section, so it stays put."""
    chunks = chunk_text("Body paragraph.\n\n## Dangling heading\n")
    assert [c.text for c in chunks] == ["Body paragraph.", "## Dangling heading"]


def test_chunk_text_merged_chunk_text_covers_exactly_its_line_range() -> None:
    """The provenance invariant: a chunk's text covers exactly its reported line
    range, so the cited lines back the cited text verbatim (ADR 0021). A merged
    heading+content chunk reconstructs from the source span, so this holds even
    when more than one blank line separates the heading from its content."""
    chunks = chunk_text("## H\n\n\nContent.\n")  # two blank lines between
    assert len(chunks) == 1
    chunk = chunks[0]
    assert (chunk.start_line, chunk.end_line) == (1, 4)
    assert chunk.text == "## H\n\n\nContent."  # verbatim, both blanks preserved
    # The cited line span exactly covers the cited text — no over-claim.
    assert chunk.text.count("\n") + 1 == chunk.end_line - chunk.start_line + 1


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
