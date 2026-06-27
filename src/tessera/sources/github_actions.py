"""Ingest a snapshot of real GitHub Actions runs into evidence records.

The first **real** connector (spec 0045, ADR 0014): a committed snapshot of the
project's own CI history under ``data/github_actions/`` — run/job/step JSON and
raw failed-step logs — ingested through the **same**
:class:`tessera.ingestion.Ingester` door the synthetic sources use, with **zero
engine change** (ADR 0002 cashed a fourth time). A GitHub workflow run is just
another structured row (``Locator.table_row``); a failed step's log is just
another ``log-span`` chunk.

The point of using real data is that it does *not* look like the synthetic
corpus. Real logs are TAB-delimited ``job⇥step⇥<ISO-timestamp> <message>`` with a
UTF-8 BOM, ANSI colour codes, ``##[group]``/``##[error]`` annotations, and no
``FailedJob`` field — the failing step must be *derived* from the step whose
conclusion is ``failure`` (its successors are ``skipped``). This source does the
GitHub-specific normalization that belongs in a *source*, not the engine: it
lifts ``job``/``step`` into the locator, drops the transport noise (BOM, ANSI,
the per-line timestamp prefix), and **keeps the real message text verbatim** —
including the ``##[error]`` marker and the real failure vocabulary
(``HttpError: Not Found``, ``Would reformat: …``). That preserved divergence is
deliberate: it is the un-planted miss the saturated eval can finally measure
(spec 0046).

Determinism/offline: this module reads only the committed snapshot — never the
network. The live fetch lives in ``scripts/fetch_github_actions_snapshot.py``
(run once, pinned run ids), exactly as ``scripts/generate_salt_synthetic.py``
sits outside the runtime/eval path.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tessera.grounding import EvidenceRecord, Locator, Origin

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "github_actions"

# A run/job/step object as parsed from the GitHub Actions JSON snapshot. The
# shape is external (the GitHub API), so it is read as untyped JSON and the
# fields the source needs are coerced with str() at the boundary.
JsonObj = dict[str, Any]

# Strip ANSI SGR/CSI escape sequences — terminal rendering, not log content.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# A raw runner-log line: <job>\t<step>\t<ISO-timestamp> <message...>.
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?")

_CONCLUSION_TO_STATUS = {"failure": "failed", "success": "passed"}

# Runner logs mark a failure with this annotation (spec 0046).
_GH_ERROR_MARKER = "##[error]"
# When a (job, step) group carries an error marker, its error cluster is split
# into its own chunk so the failure is not diluted by the dozens of lines of
# provisioning boilerplate above it (spec 0064 / ADR 0017): the real Pages-deploy
# 404 sat at lines 50–57 of a 60-line group, so the concise run-status row
# out-ranked the whole-log chunk. A few lines ride along ahead of the marker so
# the diagnostic immediately above it (e.g. a formatter's ``Would reformat:``
# lines, printed just before the non-zero exit) is not severed from the error it
# explains. A documented, tunable knob.
_ERROR_CONTEXT_LINES = 3


@dataclass(frozen=True)
class _LogChunk:
    """One citable span of a runner log.

    ``name`` is the **stable, role-tagged** id suffix (ADR 0017): ``chunk{n}``
    for an ordinary/context span, ``error{n}`` for an isolated error cluster.
    Role-derived rather than positional, so re-chunking the surrounding context
    never renames the error span a gold case cites.
    """

    job: str
    step: str
    name: str
    start_line: int
    end_line: int
    text: str


def _clean_message(rest: str) -> str:
    """Drop the per-line ISO timestamp and ANSI codes; keep the message
    verbatim — ``##[error]``/``##[group]`` markers and real vocabulary stay."""
    return _ANSI.sub("", _TIMESTAMP.sub("", rest)).rstrip()


def _make_chunk(
    job: str, step: str, name: str, lines: list[tuple[int, str]]
) -> _LogChunk:
    return _LogChunk(
        job=job,
        step=step,
        name=name,
        start_line=lines[0][0],
        end_line=lines[-1][0],
        text="\n".join(message for _, message in lines),
    )


def parse_log_chunks(raw: str) -> list[_LogChunk]:
    """Split a ``--log-failed`` dump into citable spans of the failed step's log.

    First group consecutive (job, step) lines (``job⇥step⇥<timestamp> message``;
    the BOM on the first line is stripped). Then, within any group carrying an
    ``##[error]`` marker, isolate the error cluster — the marker (minus a small
    leading context window) through the end of the group — into its own
    ``error{n}`` chunk, leaving the preamble as a ``chunk{n}``. Groups with no
    error stay a single ``chunk{n}``. This de-dilutes long runner logs so the
    actual failure line surfaces, not just the run-status row (spec 0064).
    """
    groups: list[tuple[str, str, list[tuple[int, str]]]] = []
    job = step = ""
    current: list[tuple[int, str]] = []

    for lineno, line in enumerate(raw.lstrip("﻿").splitlines(), start=1):
        parts = line.split("\t", 2)
        if len(parts) < 3:
            # A continuation line with no job/step prefix: keep it in the group.
            if current:
                current.append((lineno, _clean_message(line)))
            continue
        line_job, line_step, rest = parts
        if (line_job, line_step) != (job, step):
            if current:
                groups.append((job, step, current))
            job, step, current = line_job, line_step, []
        current.append((lineno, _clean_message(rest)))
    if current:
        groups.append((job, step, current))

    chunks: list[_LogChunk] = []
    chunk_n = error_n = 0
    for g_job, g_step, lines in groups:
        error_at = next(
            (i for i, (_, msg) in enumerate(lines) if _GH_ERROR_MARKER in msg), None
        )
        if error_at is None:
            chunk_n += 1
            chunks.append(_make_chunk(g_job, g_step, f"chunk{chunk_n}", lines))
            continue
        split = max(0, error_at - _ERROR_CONTEXT_LINES)
        preamble, failure = lines[:split], lines[split:]
        if preamble:
            chunk_n += 1
            chunks.append(_make_chunk(g_job, g_step, f"chunk{chunk_n}", preamble))
        error_n += 1
        chunks.append(_make_chunk(g_job, g_step, f"error{error_n}", failure))
    return chunks


@dataclass(frozen=True)
class GitHubActionsSource:
    """Ingester for the committed GitHub Actions snapshot (spec 0045)."""

    data_dir: Path = DATA_DIR

    def _snapshot_date(self) -> str:
        manifest = json.loads((self.data_dir / "MANIFEST.json").read_text("utf-8"))
        return str(manifest["snapshot_date"])

    def _runs(self) -> Iterator[JsonObj]:
        for path in sorted((self.data_dir / "runs").glob("*.json")):
            yield json.loads(path.read_text("utf-8"))

    def ingest(self) -> list[EvidenceRecord]:
        ingested_at = self._snapshot_date()
        return self._run_rows(ingested_at) + self._log_chunks(ingested_at)

    # --- the two record families --------------------------------------------------
    def _run_rows(self, ingested_at: str) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for row_number, run in enumerate(self._runs(), start=1):
            run_id = str(run["databaseId"])
            records.append(
                EvidenceRecord(
                    id=f"Run:{run_id}",
                    origin=Origin(
                        source=f"github_actions/runs/{run_id}.json",
                        locator=Locator.table_row("Run", row_number),
                        ingested_at=ingested_at,
                    ),
                    text=_run_text(run),
                )
            )
        return records

    def _log_chunks(self, ingested_at: str) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for path in sorted((self.data_dir / "logs").glob("*.failed.log")):
            run_id = path.name.split(".", 1)[0]
            for chunk in parse_log_chunks(path.read_text("utf-8")):
                locator = Locator(
                    kind="log-span",
                    parts=(
                        ("lines", f"{chunk.start_line}-{chunk.end_line}"),
                        ("job", chunk.job),
                        ("step", chunk.step),
                        ("section", chunk.name),
                    ),
                )
                records.append(
                    EvidenceRecord(
                        id=f"{run_id}.failed:{chunk.name}",
                        origin=Origin(
                            source=f"github_actions/logs/{path.name}",
                            locator=locator,
                            ingested_at=ingested_at,
                        ),
                        text=chunk.text,
                    )
                )
        return records

    # --- graph accessors (GitHub schema knowledge stays in the source) ------------
    def node_attributes(self) -> dict[str, tuple[tuple[str, str], ...]]:
        """Structured run facts so answer paths need not parse text — status,
        the *derived* failing job/step, commit, start time, workflow, event."""
        attrs: dict[str, tuple[tuple[str, str], ...]] = {}
        for run in self._runs():
            run_id = str(run["databaseId"])
            failed_job, failed_step = _derive_failure(run)
            attrs[f"Run:{run_id}"] = (
                ("status", _status(run)),
                ("failed_job", failed_job),
                ("failed_step", failed_step),
                ("commit", str(run.get("headSha", ""))),
                ("started", str(run.get("createdAt", ""))),
                ("workflow", str(run.get("workflowName", ""))),
                ("event", str(run.get("event", ""))),
            )
        return attrs

    def structural_edges(self) -> list[tuple[str, str, str]]:
        """Each failed-step log chunk links to its run (the ``log_of`` relation,
        exactly as the synthetic logs do)."""
        edges: list[tuple[str, str, str]] = []
        for path in sorted((self.data_dir / "logs").glob("*.failed.log")):
            run_id = path.name.split(".", 1)[0]
            for chunk in parse_log_chunks(path.read_text("utf-8")):
                edges.append(
                    (f"{run_id}.failed:{chunk.name}", f"Run:{run_id}", "log_of")
                )
        return edges


def _status(run: JsonObj) -> str:
    conclusion = str(run.get("conclusion", ""))
    return _CONCLUSION_TO_STATUS.get(conclusion, conclusion)


def _derive_failure(run: JsonObj) -> tuple[str, str]:
    """The failing (job, step): there is no ``FailedJob`` field in real data, so
    find the first step whose conclusion is ``failure`` (its successors are
    ``skipped``). Empty for a passed run."""
    jobs = run.get("jobs") or []
    for job in jobs:
        if job.get("conclusion") == "failure":
            for step in job.get("steps") or []:
                if step.get("conclusion") == "failure":
                    return str(job["name"]), str(step["name"])
            return str(job["name"]), ""
    return "", ""


def _run_text(run: JsonObj) -> str:
    failed_job, failed_step = _derive_failure(run)
    if _status(run) == "failed":
        where = f' (failing step "{failed_step}" in job "{failed_job}")'
        outcome = f"failed{where}"
    else:
        outcome = _status(run)
    return (
        f'Run {run["databaseId"]} of workflow "{run.get("workflowName", "")}" '
        f"({run.get('event', '')} on {run.get('headBranch', '')}): "
        f"status {outcome}, commit {run.get('headSha', '')}, "
        f'started {run.get("createdAt", "")} — "{run.get("displayTitle", "")}".'
    )
