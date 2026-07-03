"""The per-repo smoke battery (spec 0119) over synthetic committed fixtures.

No foreign data and no network: each test writes a workspace in the connector's
on-disk format, then runs the derived checks. The battery's own logic is thus
CI-covered while the real foreign snapshots it is meant for stay uncommitted.
"""

from __future__ import annotations

import json
from pathlib import Path

from tessera.connect.smoke import Outcome, SmokeReport, run_smoke
from tessera.connect.workspace import load_workspace

RUN_FAILED = "900000002"
RUN_PASSED = "900000001"


def _run_json(
    run_id: str, conclusion: str, *, failed_step: bool = True
) -> dict[str, object]:
    step_conclusion = "failure" if conclusion == "failure" else "success"
    return {
        "databaseId": int(run_id),
        "workflowName": "CI",
        "displayTitle": f"run {run_id}",
        "headBranch": "main",
        "headSha": "abc123",
        "event": "push",
        "conclusion": conclusion,
        "createdAt": f"2026-07-0{run_id[-1]}T10:00:00Z",
        "jobs": [
            {
                "name": "test",
                "conclusion": conclusion,
                "status": "completed",
                "steps": [
                    {
                        "number": 1,
                        "name": "Run pytest" if failed_step else "Set up",
                        "conclusion": step_conclusion,
                    }
                ],
            }
        ],
    }


def _write_workspace(
    tmp_path: Path,
    *,
    runs: dict[str, str],
    logs: dict[str, str],
    repo: str = "acme/widgets",
) -> Path:
    """Write a minimal workspace: run rows, failed logs, and a manifest."""
    root = tmp_path / "connect"
    ws = root / repo.replace("/", "-")
    (ws / "runs").mkdir(parents=True)
    (ws / "logs").mkdir()
    (ws / "prs").mkdir()
    for run_id, conclusion in runs.items():
        (ws / "runs" / f"{run_id}.json").write_text(
            json.dumps(_run_json(run_id, conclusion)) + "\n", "utf-8"
        )
    for run_id, log in logs.items():
        (ws / "logs" / f"{run_id}.failed.log").write_text(log, "utf-8")
    manifest = {
        "repo": repo,
        "snapshot_date": "2026-07-03",
        "failed_run_ids_with_logs": [int(i) for i in logs],
        "omitted_failed_run_ids": [],
        "excluded_runs": {},
    }
    (ws / "MANIFEST.json").write_text(json.dumps(manifest) + "\n", "utf-8")
    return root


def _log(run_id: str, error_line: str) -> str:
    # The gh-CLI TSV shape the source parses (job⇥step⇥<ts> message).
    return (
        "\n".join(
            [
                f"test\tRun pytest\t2026-07-02T10:05:00.0Z Running {run_id}",
                f"test\tRun pytest\t2026-07-02T10:05:01.0Z {error_line}",
            ]
        )
        + "\n"
    )


def _outcomes(report: SmokeReport) -> dict[str, Outcome]:
    return {check.name: check.outcome for check in report.checks}


def test_healthy_snapshot_passes_all_checks(tmp_path: Path) -> None:
    root = _write_workspace(
        tmp_path,
        runs={RUN_FAILED: "failure", RUN_PASSED: "success"},
        logs={RUN_FAILED: _log(RUN_FAILED, "##[error]ImportError: no module named x")},
    )
    report = run_smoke(load_workspace("acme/widgets", root=root))
    outcomes = _outcomes(report)
    assert report.ok
    assert outcomes["runs-parse"] == Outcome.PASS
    assert outcomes["failed-run-grounds"] == Outcome.PASS
    assert outcomes["claims-supported"] == Outcome.PASS
    assert outcomes["provenance-resolves"] == Outcome.PASS
    assert outcomes["refusals-fire"] == Outcome.PASS
    assert "recurrence-signal" not in outcomes  # specific signature, no warning


def test_metadata_only_snapshot_skips_grounding_honestly(tmp_path: Path) -> None:
    # A failed run row but no log (metadata-only) → grounding is SKIP, not FAIL.
    root = _write_workspace(
        tmp_path, runs={RUN_FAILED: "failure", RUN_PASSED: "success"}, logs={}
    )
    report = run_smoke(load_workspace("acme/widgets", root=root))
    outcomes = _outcomes(report)
    assert report.ok  # a skip does not fail the run
    assert outcomes["failed-run-grounds"] == Outcome.SKIP
    assert outcomes["refusals-fire"] == Outcome.PASS
    assert "claims-supported" not in outcomes  # not exercised without a log


def test_recurrence_trailer_warns(tmp_path: Path) -> None:
    # Two failed runs whose only error line is the generic exit-code trailer →
    # the RCA emits a recurrence claim on the trailer → WARN (spec 0118 caveat).
    trailer = "##[error]Process completed with exit code 1."
    older = "900000000"
    root = _write_workspace(
        tmp_path,
        runs={RUN_FAILED: "failure", older: "failure"},
        logs={RUN_FAILED: _log(RUN_FAILED, trailer), older: _log(older, trailer)},
    )
    report = run_smoke(load_workspace("acme/widgets", root=root))
    outcomes = _outcomes(report)
    assert report.ok  # warn is not a failure — provenance still holds
    assert outcomes["recurrence-signal"] == Outcome.WARN
    assert outcomes["claims-supported"] == Outcome.PASS


def test_empty_snapshot_fails_runs_parse(tmp_path: Path) -> None:
    root = _write_workspace(tmp_path, runs={}, logs={})
    report = run_smoke(load_workspace("acme/widgets", root=root))
    assert not report.ok
    assert _outcomes(report)["runs-parse"] == Outcome.FAIL


def test_provenance_resolver_catches_a_missing_cited_file(tmp_path: Path) -> None:
    # The graph is built from workspace files, so a healthy snapshot always
    # resolves. To exercise the FAIL branch, build the answer, then delete a
    # cited file and re-run the resolver directly — it must flag it.
    from tessera.connect.smoke import _unresolvable_origins
    from tessera.connect.workspace import (
        answer_workspace,
        build_workspace_graph,
        build_workspace_kb,
    )

    root = _write_workspace(
        tmp_path,
        runs={RUN_FAILED: "failure"},
        logs={RUN_FAILED: _log(RUN_FAILED, "##[error]boom")},
    )
    ws = load_workspace("acme/widgets", root=root)
    graph = build_workspace_graph(ws)
    kb = build_workspace_kb(ws)
    _, answer = answer_workspace(f"Why did run {RUN_FAILED} fail?", graph, kb)
    assert _unresolvable_origins(answer, ws) == []  # intact

    (ws.path / "logs" / f"{RUN_FAILED}.failed.log").unlink()
    missing = _unresolvable_origins(answer, ws)
    assert missing and any("logs/" in m for m in missing)
