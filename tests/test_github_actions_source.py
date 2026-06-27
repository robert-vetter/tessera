"""The real GitHub Actions connector ingests the committed snapshot through the
same door as the synthetic sources, preserving the real-log divergence.

These tests pin the properties the next unit's measured miss depends on: real
logs carry ``##[error]`` (not the synthetic ``ERROR <svc>:`` shape), the failing
step is derived (no ``FailedJob`` field), and the two Pages failures share a
recurrence fragment.
"""

from __future__ import annotations

from tessera.devex.knowledge import build_github_actions_graph
from tessera.sources.github_actions import GitHubActionsSource, parse_log_chunks

RUFF_FAILURE = "Run:27014662820"  # CI — "Format check" step failed
PAGES_FAILURE_A = "Run:27285174461"  # Docs — Pages deploy 404
PAGES_FAILURE_B = "Run:27284786811"  # Docs — same 404, earlier push (recurrence)
CI_SUCCESS = "Run:27411838436"  # dependabot CI run, passed


def _records() -> dict[str, str]:
    return {r.id: r.text for r in GitHubActionsSource().ingest()}


def test_ingests_run_rows_and_failed_step_logs() -> None:
    records = list(GitHubActionsSource().ingest())
    run_rows = [r for r in records if r.origin.locator.kind == "table-row"]
    log_chunks = [r for r in records if r.origin.locator.kind == "log-span"]
    # Five snapshotted runs; only the three failures have a failed-log.
    assert len(run_rows) == 5
    assert len(log_chunks) >= 3
    # ADR 0002 cashed a fourth time: only the existing kinds appear.
    assert {r.origin.locator.kind for r in records} <= {"table-row", "log-span"}


def test_every_record_has_a_snapshot_origin() -> None:
    for record in GitHubActionsSource().ingest():
        assert record.origin.source.startswith("github_actions/")
        # ingested_at is the MANIFEST snapshot date, never wall-clock.
        assert record.origin.ingested_at == "2026-06-16"


def test_run_row_derives_the_failing_step() -> None:
    text = _records()[RUFF_FAILURE]
    assert "status failed" in text
    # No FailedJob column exists; the failing step is derived from conclusions.
    assert 'failing step "Format check" in job "gate"' in text


def test_passed_run_has_no_failing_step() -> None:
    attrs = dict(GitHubActionsSource().node_attributes()[CI_SUCCESS])
    assert attrs["status"] == "passed"
    assert attrs["failed_job"] == ""
    assert attrs["failed_step"] == ""


def test_real_logs_carry_github_markers_not_the_synthetic_error_shape() -> None:
    # The whole point of a real connector: the divergence is preserved, so the
    # saturated eval can finally measure a miss (spec 0046). Real failures are
    # marked ``##[error]`` — the synthetic RCA heuristic keys on a bare "ERROR".
    records = list(GitHubActionsSource().ingest())
    log_text = "\n".join(r.text for r in records if r.origin.locator.kind == "log-span")
    assert "##[error]" in log_text
    assert "Would reformat" in log_text  # real ruff failure vocabulary
    assert "HttpError: Not Found" in log_text  # real Pages-deploy failure vocabulary
    # The synthetic shape the current RCA error-detector looks for is absent.
    assert "ERROR payments-service" not in log_text


def test_two_pages_failures_share_a_recurrence_fragment() -> None:
    records = {r.id: r for r in GitHubActionsSource().ingest()}
    chunks_a = [
        r.text for r in records.values() if r.id.startswith("27285174461.failed:")
    ]
    chunks_b = [
        r.text for r in records.values() if r.id.startswith("27284786811.failed:")
    ]
    text_a, text_b = "\n".join(chunks_a), "\n".join(chunks_b)
    # A stable signature recurs across both runs (the variable build version /
    # Request ID lines do not) — real material for cross-run recurrence.
    assert "##[error]HttpError: Not Found" in text_a
    assert "##[error]HttpError: Not Found" in text_b


def test_ingestion_is_deterministic() -> None:
    first = [(r.id, r.text) for r in GitHubActionsSource().ingest()]
    second = [(r.id, r.text) for r in GitHubActionsSource().ingest()]
    assert first == second


def test_graph_links_failed_logs_to_their_run() -> None:
    graph = build_github_actions_graph()
    run_nodes = {n.id for n in graph.nodes if n.kind == "Run"}
    doc_nodes = {n.id for n in graph.nodes if n.kind == "document"}
    assert RUFF_FAILURE in run_nodes
    assert len(run_nodes) == 5
    assert doc_nodes  # the failed-step log chunks
    # Every failed-log chunk links to its run via the same log_of relation the
    # synthetic logs use.
    ruff_chunks = graph.sources_of({RUFF_FAILURE}, "log_of")
    assert ruff_chunks
    assert all(cid.startswith("27014662820.failed:") for cid in ruff_chunks)


# --- finer chunking: the error cluster is isolated and de-diluted (spec 0064) ---


def test_error_cluster_is_isolated_and_de_diluted() -> None:
    """A long runner log splits into a boilerplate ``chunk1`` and the isolated
    ``error1`` cluster, so the failure is no longer buried under ~50 lines of
    provisioning. The error chunk keeps a few lines of diagnostic context above
    the marker, so the formatter's ``Would reformat`` lines stay attached."""
    recs = {
        r.id: r
        for r in GitHubActionsSource().ingest()
        if r.origin.locator.kind == "log-span"
    }
    # Pages-deploy: a 60-line group → preamble chunk + a SHORT error chunk that
    # carries the 404 cause itself (the spec 0058 dilution, removed).
    assert "27285174461.failed:chunk1" in recs  # the preamble is still citable
    pages_error = recs["27285174461.failed:error1"]
    assert len(pages_error.text.splitlines()) < 20  # was the full 60-line log
    for line in (
        "HttpError: Not Found",
        "status: 404",
        "Ensure GitHub Pages has been enabled",
    ):
        assert line in pages_error.text
    # ruff: the error chunk keeps the diagnostic just above the exit marker.
    ruff_error = recs["27014662820.failed:error1"]
    assert "Would reformat" in ruff_error.text
    assert "##[error]Process completed with exit code 1." in ruff_error.text


def test_chunk_ids_are_stable_role_tagged_not_positional() -> None:
    """Ids are role-derived (``chunk{n}``/``error{n}``, ADR 0017), so a gold case
    cites the failure cluster by a name that survives re-chunking of context."""
    log = (
        GitHubActionsSource().data_dir / "logs" / "27285174461.failed.log"
    ).read_text("utf-8")
    chunks = parse_log_chunks(log)
    assert [c.name for c in chunks] == ["chunk1", "error1"]
    error = next(c for c in chunks if c.name == "error1")
    assert error.start_line > 40  # a late sub-span, not the whole file
