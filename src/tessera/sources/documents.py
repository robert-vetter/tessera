"""Ingest authored business documents into evidence records.

The unstructured counterpart to :mod:`tessera.sources.salt`: it reads the
markdown corpus under ``data/business_docs/`` and emits
:class:`~tessera.grounding.EvidenceRecord` through the **same**
:class:`tessera.ingestion.Ingester` contract the structured source uses — so a
contract clause and a database row arrive at the graph through one door, neither
privileged (Pillar 1).

Each document is split into paragraph chunks by the engine's source-neutral
:func:`tessera.ingestion.chunk_text`; every chunk becomes one record with a
``doc-span`` locator (its line range + chunk index), so a claim can point at the
exact lines behind it. Ids are stable (``<stem>:chunk<n>``) and ``ingested_at`` is
the corpus snapshot date from ``MANIFEST.json``, so ingestion is deterministic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.ingestion import chunk_text

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "business_docs"


@dataclass(frozen=True)
class DocumentSource:
    """Ingester for the authored business-document corpus."""

    data_dir: Path = DATA_DIR

    def ingest(self) -> list[EvidenceRecord]:
        manifest = json.loads((self.data_dir / "MANIFEST.json").read_text("utf-8"))
        ingested_at = str(manifest["snapshot_date"])
        filenames = sorted(str(name) for name in manifest["documents"])

        records: list[EvidenceRecord] = []
        for filename in filenames:
            path = self.data_dir / filename
            text = path.read_text("utf-8")
            for index, chunk in enumerate(chunk_text(text), start=1):
                origin = Origin(
                    source=f"business_docs/{filename}",
                    locator=Locator.doc_span(chunk.start_line, chunk.end_line, index),
                    ingested_at=ingested_at,
                )
                records.append(
                    EvidenceRecord(
                        id=f"{path.stem}:chunk{index}",
                        origin=origin,
                        text=chunk.text,
                    )
                )
        return records
