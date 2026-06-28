"""The ingestion engine — one intake path into the common representation.

This module is deliberately *vertical-neutral and source-neutral*: it defines
what it means to be an ingester (the "one door" every source comes through) and
offers a tiny stdlib CSV reader, but it knows nothing about SALT, business data,
or any particular schema. Source-specific knowledge lives under
``tessera.sources`` (e.g. :mod:`tessera.sources.salt`), so the engine stays
general per the principles in ``CLAUDE.md``.

The contract is small on purpose: an ingester turns a source into a stream of
:class:`~tessera.grounding.EvidenceRecord`, each already carrying its
:class:`~tessera.grounding.Origin`. Unit 2's document ingester implements the
same :class:`Ingester` protocol, so structured and unstructured data arrive at
the graph through the same door — neither privileged.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from tessera.grounding import EvidenceRecord

# A *pure* ATX Markdown heading: one to six '#', then at least one space/tab,
# then content. The mandatory whitespace is the safety boundary (ADR 0021): it
# never matches GitHub-style runner-log markers (``##[error]`` — '[' is not
# whitespace), so the shared chunker leaves log corpora untouched, and a bare
# '#'/'###' with no content is not a heading.
_ATX_HEADING = re.compile(r"^#{1,6}[ \t]+\S")


@runtime_checkable
class Ingester(Protocol):
    """Anything that can turn a source into origin-tagged evidence records."""

    def ingest(self) -> Iterable[EvidenceRecord]: ...


@dataclass(frozen=True)
class TextChunk:
    """A paragraph-sized span of a text source, with its 1-based line range."""

    start_line: int
    end_line: int
    text: str


def _is_heading_block(chunk: TextChunk) -> bool:
    """True iff a chunk is a single line that is a pure ATX Markdown heading.

    A lone heading should *lead* the section it introduces, not stand alone as a
    short, term-dense record that competes with its own content in retrieval
    (ADR 0021). Single-line is required: a heading already glued to content with
    no blank line between them is one block and needs no merge.
    """
    return "\n" not in chunk.text and _ATX_HEADING.match(chunk.text) is not None


def chunk_text(text: str) -> list[TextChunk]:
    """Split text into paragraph chunks separated by blank lines.

    Source-neutral: any unstructured text source can reuse this to break a
    document into citable spans while preserving the line range each span came
    from (so a claim can point at the exact lines behind it). Deterministic — the
    same text always yields the same chunks.

    A lone Markdown heading is merged into the block that follows it, so the
    heading leads its section's first content chunk instead of becoming a
    competing heading-only record (ADR 0021). Consecutive headings chain onto the
    next content block; a trailing heading with no following content stays its own
    chunk.
    """
    lines = text.splitlines()
    blocks: list[TextChunk] = []
    buffer: list[str] = []
    start = 0
    for lineno, line in enumerate(lines, start=1):
        if line.strip():
            if not buffer:
                start = lineno
            buffer.append(line)
        elif buffer:
            blocks.append(TextChunk(start, start + len(buffer) - 1, "\n".join(buffer)))
            buffer = []
    if buffer:
        blocks.append(TextChunk(start, start + len(buffer) - 1, "\n".join(buffer)))

    # Second pass: a heading block leads the section it introduces. Fold leading
    # heading blocks onto the next content block, reconstructing the merged text
    # from the *verbatim source span* (not a re-joined approximation) so a chunk's
    # text always covers exactly its reported line range — the provenance
    # invariant that the cited lines back the cited text, even across the blank
    # separator line(s) between a heading and its content.
    chunks: list[TextChunk] = []
    pending: list[TextChunk] = []
    for block in blocks:
        if _is_heading_block(block):
            pending.append(block)
            continue
        if pending:
            start_line = pending[0].start_line
            merged_text = "\n".join(lines[start_line - 1 : block.end_line])
            chunks.append(TextChunk(start_line, block.end_line, merged_text))
            pending = []
        else:
            chunks.append(block)
    chunks.extend(pending)  # trailing heading(s) with no following content
    return chunks


def read_csv_rows(path: Path) -> Iterator[dict[str, str]]:
    """Yield each data row of a CSV as a ``{column: value}`` mapping.

    A thin wrapper over the stdlib :class:`csv.DictReader` — the runtime needs no
    heavier dependency to read the committed sample.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)
