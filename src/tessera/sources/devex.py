"""Ingest the synthetic DevEx dataset into evidence records.

The DevEx counterpart to :mod:`tessera.sources.salt` + :mod:`~.documents`:
CI/CD pipeline runs and their logs, pull requests and their diffs, ticket
history, the service catalog, and the on-call export under
``data/devex_synthetic/`` (spec 0026) — all through the **same**
:class:`tessera.ingestion.Ingester` door the business sources use. A log
line and a database row are the same kind of thing here: an
:class:`~tessera.grounding.EvidenceRecord` with a mandatory origin.

Two new :class:`~tessera.grounding.Locator` kinds appear — ``log-span``
(lines + job section + chunk) and ``diff-hunk`` (file + hunk + lines) —
constructed directly on the unchanged, kind-tagged ``Locator`` type: the
third source family to cash in ADR 0002's forward-compatibility without any
engine change. Logs are chunked by the engine's source-neutral
:func:`tessera.ingestion.chunk_text` (the log format's blank-line-separated
job sections meet the existing contract); diffs are chunked per hunk, which
is a *diff's* natural citable span — that knowledge belongs here, in the
source, not in the engine.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.ingestion import chunk_text, read_csv_rows

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "devex_synthetic"


def _component_text(row: dict[str, str]) -> str:
    return (
        f'Component {row["Component"]}: "{row["Name"]}" — '
        f"team {row['Team']}, repo {row['Repo']}."
    )


def _owner_text(row: dict[str, str]) -> str:
    return (
        f'Service "{row["Service"]}": on-call {row["OnCall"]}, '
        f"channel {row['Channel']}."
    )


def _pipeline_text(row: dict[str, str]) -> str:
    return (
        f'Pipeline {row["Pipeline"]}: "{row["Name"]}", '
        f"builds component {row['Component']}."
    )


def _run_text(row: dict[str, str]) -> str:
    outcome = (
        f"failed (failing job {row['FailedJob']})"
        if row["Status"] == "failed"
        else "passed"
    )
    return (
        f"Run {row['Run']} of pipeline {row['Pipeline']}: status {outcome}, "
        f"commit {row['Commit']}, branch {row['Branch']}, "
        f"started {row['StartedAt']}."
    )


def _ticket_text(row: dict[str, str]) -> str:
    dates = f"created {row['CreatedOn']}"
    if row["ResolvedOn"]:
        dates += f", resolved {row['ResolvedOn']}"
    return (
        f"Ticket {row['Ticket']} ({row['Type']}, {row['Status']}) for component "
        f'{row["Component"]}: "{row["Title"]}" — {row["Description"]} ({dates}).'
    )


def _pr_text(row: dict[str, str]) -> str:
    return (
        f'PR {row["PR"]}: "{row["Title"]}" by {row["Author"]}, '
        f"branch {row['Branch']}, merged commit {row['MergedCommit']} "
        f"on {row['MergedOn']} — {row['Description']}"
    )


# (table, filename, natural key column, row rendering)
_TABLES: tuple[tuple[str, str, str, Callable[[dict[str, str]], str]], ...] = (
    ("Component", "components.csv", "Component", _component_text),
    ("Owner", "owners.csv", "Service", _owner_text),
    ("Pipeline", "pipelines.csv", "Pipeline", _pipeline_text),
    ("Run", "runs.csv", "Run", _run_text),
    ("Ticket", "tickets.csv", "Ticket", _ticket_text),
    ("PR", "prs.csv", "PR", _pr_text),
)


def _log_section(chunk_first_line: str) -> str:
    """The job section a log chunk belongs to, from its first line."""
    if chunk_first_line.startswith("--- job: "):
        return chunk_first_line.removeprefix("--- job: ").removesuffix(" ---")
    if chunk_first_line.startswith("=== result:"):
        return "result"
    return "header"


@dataclass(frozen=True)
class _Hunk:
    """One citable span of a unified diff: a hunk plus its file header."""

    file: str
    start_line: int
    end_line: int
    text: str


def split_diff_hunks(text: str) -> list[_Hunk]:
    """Split a unified diff into per-hunk spans (1-based line ranges).

    A hunk's text starts with its ``diff --git`` file header so each chunk is
    self-describing evidence; ``---``/``+++`` marker lines stay part of the
    span they belong to.
    """
    hunks: list[_Hunk] = []
    file_header = ""
    file_path = ""
    current: list[str] = []
    start = 0

    def flush(end: int) -> None:
        if current:
            hunks.append(
                _Hunk(
                    file=file_path,
                    start_line=start,
                    end_line=end,
                    text="\n".join([file_header, *current]),
                )
            )
            current.clear()

    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.startswith("diff --git "):
            flush(lineno - 1)
            file_header = line
            file_path = line.split(" b/")[-1]
        elif line.startswith("@@"):
            flush(lineno - 1)
            start = lineno
            current.append(line)
        elif current:
            current.append(line)
    flush(len(text.splitlines()))
    return hunks


@dataclass(frozen=True)
class DevExSource:
    """Ingester for the committed synthetic DevEx dataset (spec 0026/0027)."""

    data_dir: Path = DATA_DIR

    def _snapshot_date(self) -> str:
        manifest = json.loads((self.data_dir / "MANIFEST.json").read_text("utf-8"))
        return str(manifest["snapshot_date"])

    def ingest(self) -> list[EvidenceRecord]:
        ingested_at = self._snapshot_date()
        records = self._structured(ingested_at)
        records += self._logs(ingested_at)
        records += self._diffs(ingested_at)
        return records

    # --- the three record families ------------------------------------------------
    def _structured(self, ingested_at: str) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for table, filename, key_column, text_fn in _TABLES:
            for row_number, row in enumerate(
                read_csv_rows(self.data_dir / filename), start=1
            ):
                records.append(
                    EvidenceRecord(
                        id=f"{table}:{row[key_column]}",
                        origin=Origin(
                            source=f"devex_synthetic/{filename}",
                            locator=Locator.table_row(table, row_number),
                            ingested_at=ingested_at,
                        ),
                        text=text_fn(row),
                    )
                )
        return records

    def _logs(self, ingested_at: str) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for path in sorted((self.data_dir / "logs").glob("*.log")):
            text = path.read_text("utf-8")
            for index, chunk in enumerate(chunk_text(text), start=1):
                section = _log_section(chunk.text.splitlines()[0])
                locator = Locator(
                    kind="log-span",
                    parts=(
                        ("lines", f"{chunk.start_line}-{chunk.end_line}"),
                        ("section", section),
                        ("chunk", str(index)),
                    ),
                )
                records.append(
                    EvidenceRecord(
                        id=f"{path.stem}:chunk{index}",
                        origin=Origin(
                            source=f"devex_synthetic/logs/{path.name}",
                            locator=locator,
                            ingested_at=ingested_at,
                        ),
                        text=chunk.text,
                    )
                )
        return records

    def _diffs(self, ingested_at: str) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for path in sorted((self.data_dir / "prs").glob("*.diff")):
            for index, hunk in enumerate(split_diff_hunks(path.read_text("utf-8")), 1):
                locator = Locator(
                    kind="diff-hunk",
                    parts=(
                        ("file", hunk.file),
                        ("hunk", str(index)),
                        ("lines", f"{hunk.start_line}-{hunk.end_line}"),
                    ),
                )
                records.append(
                    EvidenceRecord(
                        id=f"{path.stem}.diff:hunk{index}",
                        origin=Origin(
                            source=f"devex_synthetic/prs/{path.name}",
                            locator=locator,
                            ingested_at=ingested_at,
                        ),
                        text=hunk.text,
                    )
                )
        return records
