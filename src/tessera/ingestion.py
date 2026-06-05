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
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from tessera.grounding import EvidenceRecord


@runtime_checkable
class Ingester(Protocol):
    """Anything that can turn a source into origin-tagged evidence records."""

    def ingest(self) -> Iterable[EvidenceRecord]: ...


def read_csv_rows(path: Path) -> Iterator[dict[str, str]]:
    """Yield each data row of a CSV as a ``{column: value}`` mapping.

    A thin wrapper over the stdlib :class:`csv.DictReader` — the runtime needs no
    heavier dependency to read the committed sample.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)
