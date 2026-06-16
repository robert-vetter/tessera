#!/usr/bin/env python3
"""Snapshot a fixed set of real GitHub Actions runs into committed fixtures.

This is the **only** place in Tessera that touches the network, and it is a
run-once developer tool — never imported at runtime, never run by the gate or
the eval (cf. ``scripts/generate_salt_synthetic.py``, which is the same kind of
boundary: a dev-time generator whose committed output is the real dataset).

Why a real connector at all: every recorded eval number is 1.000, so both
synthetic batteries are saturated (ADR 0007 trigger 2). Real CI data is the
honest source of *un-planted* difficulty — its logs spell failures ``##[error]``
with nanosecond timestamps, ANSI, and TAB-delimited job/step prefixes, nothing
like the synthetic ``ERROR <svc>:`` shape the RCA heuristic keys on. Ingesting
it lets the eval measure a miss no one authored (spec 0045, ADR 0014).

Determinism / offline guarantee: the run ids are **pinned** (never "latest N",
which would change with every push), the runs are immutable GitHub history, and
``SNAPSHOT_DATE`` is a constant — so re-running reproduces byte-identical
fixtures. The committed ``data/github_actions/`` tree is the dataset; the source
(:mod:`tessera.sources.github_actions`) and the eval read it offline with zero
``gh``/network/token dependency.

Usage (requires an authenticated ``gh`` CLI with read access to the repo)::

    uv run python scripts/fetch_github_actions_snapshot.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = "robert-vetter/tessera"
# A fixed, reproducible date for the snapshot — the origin "ingested_at" the
# source reads, exactly as the synthetic MANIFESTs carry a fixed snapshot_date.
SNAPSHOT_DATE = "2026-06-16"

# Pinned run ids, chosen for failure-vocabulary variety, not breadth (real CI
# failures here are dominated by one boring infra cause — see the NOTICE). Each
# is immutable GitHub history.
FAILED_RUNS = (
    27014662820,  # CI — ruff "Format check" step failed ("Would reformat …"),
    #               later steps skipped; a real *code* failure, failing step
    #               must be DERIVED (no FailedJob field). Phase-1 Unit-1 PR.
    27285174461,  # Docs — Pages deploy 404 ("##[error]HttpError: Not Found" /
    #               "Ensure GitHub Pages has been enabled"). Phase-4 close push.
    27284786811,  # Docs — the SAME Pages 404 on an earlier push: a real
    #               recurrence signal across two runs (writeup push).
)
PASSED_RUNS = (
    27411838436,  # CI — passed (dependabot ruff bump). For passed-run refusal.
    27411838417,  # Docs — passed (same dependabot PR).
)

# The fields we persist per run. Immutable; re-dumped sorted so diffs are stable
# regardless of gh's key ordering.
RUN_FIELDS = (
    "databaseId,name,workflowName,displayTitle,headBranch,headSha,"
    "event,conclusion,createdAt,jobs"
)

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "github_actions"


def _gh(*args: str) -> str:
    """Run a read-only gh command and return stdout (the one network call)."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _trim_job(job: dict[str, object]) -> dict[str, object]:
    """Keep the run/job/step shape the source needs; drop volatile URLs/ids."""
    steps = job.get("steps") or []
    return {
        "name": job["name"],
        "conclusion": job["conclusion"],
        "status": job["status"],
        "steps": [
            {
                "number": s["number"],
                "name": s["name"],
                "conclusion": s["conclusion"],
            }
            for s in steps  # type: ignore[union-attr]
        ],
    }


def _write_run(run_id: int) -> None:
    raw = json.loads(
        _gh("run", "view", str(run_id), "--repo", REPO, "--json", RUN_FIELDS)
    )
    raw["jobs"] = [_trim_job(j) for j in raw.get("jobs", [])]
    path = OUT_DIR / "runs" / f"{run_id}.json"
    path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", "utf-8")
    print(f"  wrote {path.relative_to(OUT_DIR.parent)}")


def _write_failed_log(run_id: int) -> None:
    log = _gh("run", "view", str(run_id), "--repo", REPO, "--log-failed")
    path = OUT_DIR / "logs" / f"{run_id}.failed.log"
    path.write_text(log, "utf-8")
    print(f"  wrote {path.relative_to(OUT_DIR.parent)} ({len(log)} bytes)")


def main() -> None:
    (OUT_DIR / "runs").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "logs").mkdir(parents=True, exist_ok=True)

    print(f"Snapshotting {REPO} Actions runs into {OUT_DIR} …")
    for run_id in (*FAILED_RUNS, *PASSED_RUNS):
        _write_run(run_id)
    for run_id in FAILED_RUNS:
        _write_failed_log(run_id)

    manifest = {
        "dataset": "github_actions",
        "synthetic": False,
        "source": (
            f"github.com/{REPO} — GitHub Actions API (run/job/step + raw runner logs)"
        ),
        "snapshot_date": SNAPSHOT_DATE,
        "fetched_by": "scripts/fetch_github_actions_snapshot.py",
        "failed_run_ids": list(FAILED_RUNS),
        "passed_run_ids": list(PASSED_RUNS),
    }
    (OUT_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", "utf-8"
    )
    print(f"  wrote {Path('github_actions') / 'MANIFEST.json'}")
    print("Done. Review and commit the snapshot; the gate/eval never re-fetch.")


if __name__ == "__main__":
    main()
