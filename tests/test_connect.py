"""The BYO GitHub connector: bounded fetch, scrub-before-disk, offline answers.

Everything runs against a fake transport (spec 0118: tests are offline; the
network is a dev-time action). The scenarios pin the unit's trust properties:
the snapshot lands in the committed-corpus format so the unchanged
``GitHubActionsSource`` + RCA answer over it; credential-shaped content never
reaches disk; the auth header never travels to a redirect target; caps and
divergences become named misses in the manifest, not silence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from tessera.connect.github import (
    API_ROOT,
    DEFAULT_CAPS,
    ConnectError,
    FetchCaps,
    FetchResponse,
    SnapshotResult,
    default_transport,
    fetch_snapshot,
)
from tessera.connect.scrub import SCRUB_MARKER, neutralize_controls, scrub_text
from tessera.connect.workspace import (
    InvalidTarget,
    PRSource,
    Workspace,
    WorkspaceNotConnected,
    answer_workspace,
    build_workspace_graph,
    build_workspace_kb,
    load_workspace,
)
from tessera.eval.metrics import is_supported
from tessera.sources.github_actions import parse_log_chunks

REPO = "acme/widgets"
RUNS_URL = f"{API_ROOT}/repos/acme/widgets/actions/runs?per_page=30"
JOBS_URL = (
    f"{API_ROOT}/repos/acme/widgets/actions/runs/900000002/jobs?per_page=100&page=1"
)
JOBS_URL_OLD = (
    f"{API_ROOT}/repos/acme/widgets/actions/runs/900000000/jobs?per_page=100&page=1"
)
LOG_URL = f"{API_ROOT}/repos/acme/widgets/actions/jobs/501/logs"
LOG_URL_OLD = f"{API_ROOT}/repos/acme/widgets/actions/jobs/601/logs"
BLOB_URL = "https://blob.example.test/signed/501.txt"
PULLS_URL = (
    f"{API_ROOT}/repos/acme/widgets/pulls"
    "?state=all&per_page=30&sort=created&direction=desc"
)

PLANTED_TOKEN = "ghp_" + "a1" * 12  # credential-shaped; must never reach disk

# The failed step's window is 10:05:00–10:06:00; earlier lines are setup noise.
JOB_LOG = "﻿" + "\n".join(
    [
        "2026-07-02T10:04:58.1000000Z ##[group]Run pytest -q",
        "2026-07-02T10:05:01.2000000Z collected 12 items",
        f"2026-07-02T10:05:02.3000000Z leaked credential {PLANTED_TOKEN}",
        "2026-07-02T10:05:03.4000000Z FAILED tests/test_api.py::test_rate_limit",
        "2026-07-02T10:05:04.5000000Z ##[error]Process completed with exit code 1.",
    ]
)


def _json_response(payload: object) -> FetchResponse:
    return FetchResponse(
        status=200, headers={}, body=json.dumps(payload).encode("utf-8")
    )


def _runs_listing() -> dict[str, object]:
    return {
        "total_count": 4,
        "workflow_runs": [
            {
                "id": 900000003,
                "name": "CI",
                "display_title": "still going",
                "head_branch": "main",
                "head_sha": "c3",
                "event": "push",
                "status": "in_progress",
                "conclusion": None,
                "created_at": "2026-07-02T11:00:00Z",
            },
            {
                "id": 900000002,
                "name": "CI",
                "display_title": "break the tests",
                "head_branch": "main",
                "head_sha": "c2",
                "event": "push",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-07-02T10:00:00Z",
            },
            {
                "id": 900000001,
                "name": "CI",
                "display_title": "a green one",
                "head_branch": "main",
                "head_sha": "c1",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-07-01T09:00:00Z",
            },
            {
                "id": 900000000,
                "name": "CI",
                "display_title": "an older failure",
                "head_branch": "main",
                "head_sha": "c0",
                "event": "push",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-06-30T08:00:00Z",
            },
        ],
    }


def _jobs_listing() -> dict[str, object]:
    return {
        "total_count": 2,
        "jobs": [
            {
                "id": 501,
                "name": "test (3.12)",
                "status": "completed",
                "conclusion": "failure",
                "steps": [
                    {
                        "number": 1,
                        "name": "Set up job",
                        "conclusion": "success",
                        "started_at": "2026-07-02T10:04:00Z",
                        "completed_at": "2026-07-02T10:04:59Z",
                    },
                    {
                        "number": 2,
                        "name": "Run pytest",
                        "conclusion": "failure",
                        "started_at": "2026-07-02T10:05:00Z",
                        "completed_at": "2026-07-02T10:06:00Z",
                    },
                ],
            },
            {
                "id": 502,
                "name": "lint",
                "status": "completed",
                "conclusion": "success",
                "steps": [],
            },
        ],
    }


def _pulls_listing() -> list[dict[str, object]]:
    return [
        {
            "number": 42,
            "title": "Retry rate-limited API calls",
            "state": "closed",
            "user": {"login": "dev-a"},
            "created_at": "2026-07-01T12:00:00Z",
            "merged_at": "2026-07-02T09:00:00Z",
            "head": {"ref": "fix/rate-limit"},
            "base": {"ref": "main"},
            "body": "Fixes the flaky test.\nAuthorization: Bearer abc123def456ghi",
        }
    ]


class FakeTransport:
    """Canned responses keyed by exact URL; records every request it sees."""

    def __init__(self, routes: dict[str, FetchResponse]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> FetchResponse:
        self.calls.append((url, dict(headers)))
        if url not in self.routes:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.routes[url]


def _old_jobs_listing() -> dict[str, object]:
    """The older failure's job — its log has expired on GitHub (404 path)."""
    return {
        "total_count": 1,
        "jobs": [
            {
                "id": 601,
                "name": "test (3.12)",
                "status": "completed",
                "conclusion": "failure",
                "steps": [
                    {
                        "number": 1,
                        "name": "Run pytest",
                        "conclusion": "failure",
                        "started_at": "2026-06-30T08:01:00Z",
                        "completed_at": "2026-06-30T08:02:00Z",
                    }
                ],
            }
        ],
    }


def _default_routes() -> dict[str, FetchResponse]:
    return {
        RUNS_URL: _json_response(_runs_listing()),
        JOBS_URL: _json_response(_jobs_listing()),
        JOBS_URL_OLD: _json_response(_old_jobs_listing()),
        LOG_URL: FetchResponse(status=302, headers={"location": BLOB_URL}, body=b""),
        LOG_URL_OLD: FetchResponse(status=404, headers={}, body=b"{}"),
        BLOB_URL: FetchResponse(status=200, headers={}, body=JOB_LOG.encode("utf-8")),
        PULLS_URL: _json_response(_pulls_listing()),
    }


def _connect(
    tmp_path: Path,
    transport: FakeTransport,
    *,
    token: str | None = None,
    caps: FetchCaps = DEFAULT_CAPS,
) -> SnapshotResult:
    return fetch_snapshot(
        REPO,
        tmp_path / "connect",
        transport=transport,
        snapshot_date="2026-07-03",
        fetched_at="2026-07-03T12:00:00Z",
        token=token,
        caps=caps,
    )


# --- the fetch → workspace path ----------------------------------------------------
def test_snapshot_lands_in_the_committed_corpus_format(tmp_path: Path) -> None:
    transport = FakeTransport(_default_routes())
    result = _connect(tmp_path, transport, token="tok-test")

    ws = result.workspace
    assert (ws / "MANIFEST.json").is_file()
    assert (ws / "NOTICE").is_file()
    # Passed + selected failed runs are written; the older failure fell under
    # the cap only if the cap allows — with the default cap of 5 both fit.
    assert (ws / "runs" / "900000002.json").is_file()
    assert (ws / "runs" / "900000001.json").is_file()
    # The older failure is selected too (cap 5) — its run row is kept even
    # though its log has expired upstream; the miss is named.
    assert (ws / "runs" / "900000000.json").is_file()
    assert not (ws / "logs" / "900000000.failed.log").exists()
    # The in-progress run never enters the snapshot (RCA vocabulary honesty).
    assert not (ws / "runs" / "900000003.json").exists()
    manifest = json.loads((ws / "MANIFEST.json").read_text("utf-8"))
    assert manifest["excluded_runs"] == {"900000003": "in_progress"}
    assert manifest["failed_run_ids_with_logs"] == [900000002]
    assert any("expired or never produced" in miss for miss in manifest["misses"])
    assert manifest["snapshot_date"] == "2026-07-03"
    assert manifest["token_used"] is True

    # The synthesized TSV parses with the UNCHANGED committed-corpus parser:
    # the failed step's lines only, the error cluster isolated.
    chunks = parse_log_chunks((ws / "logs" / "900000002.failed.log").read_text("utf-8"))
    assert {(c.job, c.step) for c in chunks} == {("test (3.12)", "Run pytest")}
    assert any(c.name.startswith("error") for c in chunks)
    assert all("10:04:58" not in c.text for c in chunks)  # outside the window


def test_failed_runs_beyond_the_cap_are_omitted_and_named(tmp_path: Path) -> None:
    transport = FakeTransport(_default_routes())
    result = _connect(
        tmp_path, transport, token="tok-test", caps=FetchCaps(failed_logs=1)
    )
    manifest = result.manifest
    assert manifest["failed_run_ids_with_logs"] == [900000002]
    assert manifest["omitted_failed_run_ids"] == [900000000]
    assert not (result.workspace / "runs" / "900000000.json").exists()
    assert any("omitted" in miss for miss in manifest["misses"])


def test_credential_shapes_never_reach_disk(tmp_path: Path) -> None:
    transport = FakeTransport(_default_routes())
    result = _connect(tmp_path, transport, token="tok-test")
    everything = ""
    for path in sorted(result.workspace.rglob("*")):
        if path.is_file():
            everything += path.read_text("utf-8")
    assert PLANTED_TOKEN not in everything
    assert "abc123def456ghi" not in everything  # the PR body's bearer value
    assert SCRUB_MARKER in everything
    counts = result.manifest["scrub_counts"]
    assert counts["github-token"] == 1
    assert counts["authorization-header"] == 1


def test_the_token_never_travels_to_the_redirect_target(tmp_path: Path) -> None:
    transport = FakeTransport(_default_routes())
    _connect(tmp_path, transport, token="tok-test")
    api_calls = [h for url, h in transport.calls if url.startswith(API_ROOT)]
    blob_calls = [h for url, h in transport.calls if url == BLOB_URL]
    assert api_calls and all("Authorization" in h for h in api_calls)
    assert blob_calls and all("Authorization" not in h for h in blob_calls)


def test_without_a_token_the_snapshot_is_metadata_only(tmp_path: Path) -> None:
    routes = _default_routes()
    # Log downloads must not even be attempted without a token.
    del routes[LOG_URL], routes[LOG_URL_OLD], routes[BLOB_URL]
    transport = FakeTransport(routes)
    result = _connect(tmp_path, transport, token=None)
    assert result.metadata_only is True
    assert result.manifest["token_used"] is False
    assert not list((result.workspace / "logs").glob("*"))
    # The failed run's row is still there, with its jobs metadata.
    run = json.loads((result.workspace / "runs" / "900000002.json").read_text("utf-8"))
    assert run["jobs"], "jobs metadata is public and stays in the snapshot"
    assert any("GITHUB_TOKEN" in miss for miss in result.manifest["misses"])


def test_a_step_without_a_timestamp_window_falls_back_named(tmp_path: Path) -> None:
    jobs = _jobs_listing()
    steps = jobs["jobs"][0]["steps"]  # type: ignore[index]
    steps[1]["completed_at"] = None
    routes = _default_routes()
    routes[JOBS_URL] = _json_response(jobs)
    transport = FakeTransport(routes)
    result = _connect(tmp_path, transport, token="tok-test")
    log = (result.workspace / "logs" / "900000002.failed.log").read_text("utf-8")
    # Whole-job fallback: the step column is empty, the setup line included.
    assert log.startswith("test (3.12)\t\t")
    assert "10:04:58" in log
    assert any("no usable timestamp window" in m for m in result.manifest["misses"])


def test_rate_limit_exhaustion_is_a_plain_actionable_error(tmp_path: Path) -> None:
    routes = {
        RUNS_URL: FetchResponse(
            status=403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1782000000"},
            body=b"{}",
        )
    }
    with pytest.raises(ConnectError, match="rate limit.*GITHUB_TOKEN"):
        _connect(tmp_path, FakeTransport(routes), token=None)


def test_a_missing_or_private_repo_is_a_plain_error(tmp_path: Path) -> None:
    routes = {RUNS_URL: FetchResponse(status=404, headers={}, body=b"{}")}
    with pytest.raises(ConnectError, match="does not exist, is private"):
        _connect(tmp_path, FakeTransport(routes), token=None)


def test_reconnect_replaces_the_workspace_atomically(tmp_path: Path) -> None:
    transport = FakeTransport(_default_routes())
    first = _connect(tmp_path, transport, token="tok-test")
    marker = first.workspace / "runs" / "900000001.json"
    assert marker.is_file()
    again = FakeTransport(_default_routes())
    second = fetch_snapshot(
        REPO,
        tmp_path / "connect",
        transport=again,
        snapshot_date="2026-07-04",
        fetched_at="2026-07-04T12:00:00Z",
        token="tok-test",
    )
    manifest = json.loads((second.workspace / "MANIFEST.json").read_text("utf-8"))
    assert manifest["snapshot_date"] == "2026-07-04"
    assert not list((tmp_path / "connect").glob(".tmp-*"))


# --- the offline answer path over a connected workspace ----------------------------
def _connected_workspace(tmp_path: Path) -> Workspace:
    transport = FakeTransport(_default_routes())
    _connect(tmp_path, transport, token="tok-test")
    return load_workspace(REPO, root=tmp_path / "connect")


def test_ask_grounds_an_rca_with_workspace_provenance(tmp_path: Path) -> None:
    workspace = _connected_workspace(tmp_path)
    graph = build_workspace_graph(workspace)
    kb = build_workspace_kb(workspace)
    route, answer = answer_workspace("Why did run 900000002 fail?", graph, kb)

    assert route.kind == "rca"
    assert answer.is_grounded
    # The run row + the isolated error span are both cited, and every origin
    # points into the real workspace directory (rebased provenance).
    texts = [claim.text for claim in answer.claims]
    assert any("break the tests" in text for text in texts)
    assert any("##[error]Process completed" in text for text in texts)
    for claim in answer.claims:
        for record in claim.support:
            assert record.origin.source.startswith("var/connect/acme-widgets/")
            relative = record.origin.source.removeprefix("var/connect/acme-widgets/")
            assert (workspace.path / relative).is_file()

    # Every emitted claim passes the eval's own verifier — the same check the
    # measured batteries run (harness construction mirrored).
    nodes = {node.id: node for node in graph.nodes}
    assert all(is_supported(claim, nodes, graph) for claim in answer.claims)


def test_ask_refuses_a_passed_and_an_unknown_run(tmp_path: Path) -> None:
    workspace = _connected_workspace(tmp_path)
    graph = build_workspace_graph(workspace)
    kb = build_workspace_kb(workspace)

    _, passed = answer_workspace("Why did run 900000001 fail?", graph, kb)
    assert not passed.is_grounded
    assert "did not fail" in (passed.refusal or "")

    _, unknown = answer_workspace("Why did run 777777777 fail?", graph, kb)
    assert not unknown.is_grounded
    assert "no run 777777777" in (unknown.refusal or "")


def test_lookup_route_answers_from_pr_rows(tmp_path: Path) -> None:
    workspace = _connected_workspace(tmp_path)
    prs = PRSource(workspace).ingest()
    assert [record.id for record in prs] == ["PR:42"]
    assert prs[0].origin.locator.kind == "table-row"
    assert prs[0].origin.ingested_at == "2026-07-03"

    graph = build_workspace_graph(workspace)
    kb = build_workspace_kb(workspace)
    route, answer = answer_workspace(
        "Which pull request retried rate-limited API calls?", graph, kb
    )
    assert route.kind == "lookup"
    assert answer.is_grounded
    assert any("PR #42" in claim.text for claim in answer.claims)


def test_unconnected_target_raises_with_the_command_to_run(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotConnected, match="tessera connect github"):
        load_workspace("nobody/nothing", root=tmp_path / "connect")


# --- scrubber unit coverage ---------------------------------------------------------
def test_scrub_patterns_and_counts() -> None:
    text = "\n".join(
        [
            f"token {PLANTED_TOKEN} leaked",
            "pat github_pat_ABCDEFGHIJKLMNOP1234 here",
            "key AKIAABCDEFGHIJKLMNOP in env",
            "slack xoxb-1234567890-abcdef",
            "Authorization: Bearer topsecretvalue",
            "password=hunter2hunter2",
        ]
    )
    scrubbed, counts = scrub_text(text)
    assert PLANTED_TOKEN not in scrubbed
    assert "topsecretvalue" not in scrubbed
    assert "hunter2hunter2" not in scrubbed
    assert scrubbed.count(SCRUB_MARKER) == 6
    assert counts == {
        "github-token": 1,
        "github-fine-grained-pat": 1,
        "aws-access-key": 1,
        "slack-token": 1,
        "authorization-header": 1,
        "sensitive-assignment": 1,
    }
    # Line structure survives — locators stay truthful.
    assert scrubbed.count("\n") == text.count("\n")


def test_scrub_leaves_clean_text_alone() -> None:
    text = "ERROR payments-service: TimeoutError after 30s"
    scrubbed, counts = scrub_text(text)
    assert scrubbed == text
    assert counts == {}


def test_scrub_catches_more_credential_shapes() -> None:
    # Shapes an adversarial review flagged as prior survivors (spec 0118 review).
    cases = {
        "gitlab-pat": "token glpat-ABCDEFGHIJ1234567890 here",
        "npm-token": "npm_" + "a" * 36,
        "google-api-key": "AIza" + "B" * 35,
        "openai-key": "sk-proj-" + "c" * 24,
        "jwt": "eyJ" + "a" * 12 + ".eyJ" + "b" * 12 + "." + "d" * 20,
        "sensitive-assignment": "_authToken=" + "e" * 20,
    }
    for name, text in cases.items():
        _, counts = scrub_text(text)
        assert name in counts, f"{name} not scrubbed from {text!r}: {counts}"


def test_scrub_neutralizes_terminal_control_sequences() -> None:
    # ANSI CSI, an OSC-8 hyperlink, a carriage-return overwrite, a bare BEL, and
    # a C1 CSI-equivalent — all stripped; \t and \n survive (locators/columns).
    hostile = (
        "\x1b[31mred\x1b[0m\t"
        "\x1b]8;;http://evil.test\x07label\x1b]8;;\x07\n"
        "real\rFORGED\x07\x9bmore"
    )
    cleaned, hits = neutralize_controls(hostile)
    assert "\x1b" not in cleaned and "\x07" not in cleaned and "\r" not in cleaned
    assert "\x9b" not in cleaned
    assert "\t" in cleaned and "\n" in cleaned  # structure preserved
    assert hits > 0
    _, counts = scrub_text(hostile)
    assert counts.get("control-sequences", 0) > 0


def test_scrub_patterns_do_not_cross_line_boundaries(tmp_path: Path) -> None:
    # A log line ending in "password:" (a routine prompt) must NOT let the
    # scrubber eat the next TSV line's job column (corr M2). Build a real
    # workspace whose failed-step log contains such a line and confirm the
    # parsed chunk still names the real job.
    job_log = "﻿" + "\n".join(
        [
            "2026-07-02T10:05:00.0Z ##[group]Run deploy",
            "2026-07-02T10:05:01.0Z Enter host password:",
            "2026-07-02T10:05:02.0Z ##[error]Process completed with exit code 1.",
        ]
    )
    routes = _default_routes()
    routes[BLOB_URL] = FetchResponse(status=200, headers={}, body=job_log.encode())
    result = _connect(tmp_path, FakeTransport(routes), token="tok-test")
    log = (result.workspace / "logs" / "900000002.failed.log").read_text("utf-8")
    chunks = parse_log_chunks(log)
    assert chunks and all(c.job == "test (3.12)" for c in chunks)
    assert SCRUB_MARKER not in log  # nothing credential-shaped was actually present


def test_tab_in_job_name_cannot_shift_tsv_columns(tmp_path: Path) -> None:
    jobs = _jobs_listing()
    jobs["jobs"][0]["name"] = "test\t(evil)\ninjection"  # type: ignore[index]
    routes = _default_routes()
    routes[JOBS_URL] = _json_response(jobs)
    result = _connect(tmp_path, FakeTransport(routes), token="tok-test")
    log = (result.workspace / "logs" / "900000002.failed.log").read_text("utf-8")
    chunks = parse_log_chunks(log)
    # The name is flattened to a single safe column value — no injected columns.
    assert chunks and all(c.job == "test (evil) injection" for c in chunks)


def test_manifest_misses_are_scrubbed(tmp_path: Path) -> None:
    # A credential planted in a JOB NAME reaches a miss string; that miss is
    # written to MANIFEST.json, so it too must be scrubbed (sec MAJOR-2).
    jobs = _old_jobs_listing()
    jobs["jobs"][0]["name"] = f"deploy {PLANTED_TOKEN}"  # type: ignore[index]
    jobs["jobs"][0]["steps"] = []  # type: ignore[index]  # → job-level miss w/ name
    routes = _default_routes()
    routes[JOBS_URL_OLD] = _json_response(jobs)
    routes[LOG_URL_OLD] = FetchResponse(status=200, headers={}, body=b"log\n")
    result = _connect(
        tmp_path, FakeTransport(routes), token="tok-test", caps=FetchCaps(failed_logs=5)
    )
    manifest_text = (result.workspace / "MANIFEST.json").read_text("utf-8")
    assert PLANTED_TOKEN not in manifest_text
    assert any(SCRUB_MARKER in miss for miss in result.manifest["misses"])


def test_redirect_to_non_http_scheme_is_refused(tmp_path: Path) -> None:
    routes = _default_routes()
    routes[LOG_URL] = FetchResponse(
        status=302, headers={"location": "file:///etc/passwd"}, body=b""
    )
    with pytest.raises(ConnectError, match="non-http redirect"):
        _connect(tmp_path, FakeTransport(routes), token="tok-test")


def test_non_json_200_is_a_clean_error(tmp_path: Path) -> None:
    routes = {
        RUNS_URL: FetchResponse(status=200, headers={}, body=b"<html>portal</html>")
    }
    with pytest.raises(ConnectError, match="not JSON"):
        _connect(tmp_path, FakeTransport(routes), token=None)


def test_default_transport_wraps_non_http_errors() -> None:
    # The real transport has no FileHandler, so a file:// URL raises URLError,
    # which must surface as a ConnectError (spec acceptance: clean message).
    with pytest.raises(ConnectError, match="network error"):
        default_transport("file:///etc/hosts", {})


def test_token_rejected_for_logs_gives_a_token_aware_miss(tmp_path: Path) -> None:
    routes = _default_routes()
    routes[LOG_URL] = FetchResponse(status=403, headers={}, body=b"{}")
    result = _connect(tmp_path, FakeTransport(routes), token="tok-test")
    assert any("was not accepted" in miss for miss in result.manifest["misses"])
    assert (
        result.metadata_only_reason == "failed-run logs were unavailable (see misses)"
    )


def test_green_repo_metadata_only_reason(tmp_path: Path) -> None:
    listing = _runs_listing()
    # Drop both failures → a green repo with a token: no failed-run logs, but
    # NOT because logs were unavailable.
    runs = listing["workflow_runs"]
    assert isinstance(runs, list)
    listing["workflow_runs"] = [r for r in runs if r["conclusion"] != "failure"]
    routes = {
        RUNS_URL: _json_response(listing),
        PULLS_URL: _json_response(_pulls_listing()),
    }
    result = _connect(tmp_path, FakeTransport(routes), token="tok-test")
    assert result.metadata_only is True
    assert result.metadata_only_reason == "no failed runs among the runs considered"


def test_ask_pointer_names_omitted_and_excluded_runs(tmp_path: Path) -> None:
    from tessera.connect.cli import _manifest_pointer

    manifest = {
        "omitted_failed_run_ids": [900000000],
        "excluded_runs": {"900000003": "in_progress"},
    }
    assert "omitted" in (
        _manifest_pointer("Why did run 900000000 fail?", manifest) or ""
    )
    assert "excluded" in (
        _manifest_pointer("Why did run 900000003 fail?", manifest) or ""
    )
    assert _manifest_pointer("Why did run 111111111 fail?", manifest) is None


def test_pr_body_scrubbed_then_capped_with_marker(tmp_path: Path) -> None:
    pulls = _pulls_listing()
    pulls[0]["body"] = "x" * 40 + PLANTED_TOKEN + "y" * 600  # straddles the cap
    routes = _default_routes()
    routes[PULLS_URL] = _json_response(pulls)
    result = _connect(
        tmp_path,
        FakeTransport(routes),
        token="tok-test",
        caps=FetchCaps(pr_body_chars=50),
    )
    body = json.loads((result.workspace / "prs" / "42.json").read_text("utf-8"))["body"]
    assert PLANTED_TOKEN not in body  # scrubbed BEFORE the cut, not lost past it
    assert body.endswith("…[truncated]")
    assert any("truncated" in miss for miss in result.manifest["misses"])


def test_invalid_ask_targets_are_refused(tmp_path: Path) -> None:
    for bad in ("..", ".", "", "/etc/passwd"):
        with pytest.raises(InvalidTarget):
            load_workspace(bad, root=tmp_path / "connect")


def test_workspace_repo_collision_is_flagged(tmp_path: Path) -> None:
    # a/b-c and a-b/c both map to dir "a-b-c"; loading the wrong one must error.
    root = tmp_path / "connect"
    (root / "a-b-c").mkdir(parents=True)
    (root / "a-b-c" / "MANIFEST.json").write_text('{"repo": "a-b/c"}', "utf-8")
    with pytest.raises(InvalidTarget, match="not 'a/b-c'"):
        load_workspace("a/b-c", root=root)
    # The matching target loads fine.
    assert load_workspace("a-b/c", root=root).repo == "a-b/c"


def test_cap_flags_reject_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    from tessera.connect.cli import main as connect_main

    with pytest.raises(SystemExit):
        connect_main(["connect", "github", "a/b", "--failed", "-1"])
    with pytest.raises(SystemExit):
        connect_main(["connect", "github", "a/b", "--runs", "0"])


# --- the front-door dispatcher ------------------------------------------------------
def test_dispatcher_routes_subcommands_and_falls_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tessera.business.cli as business_cli
    import tessera.cli as front_door

    seen: dict[str, object] = {}

    def fake_business(argv: list[str] | None = None) -> int:
        seen["argv"] = argv
        return 0

    monkeypatch.setattr(business_cli, "main", fake_business)
    assert front_door.main(["Which customers renew in Q3?"]) == 0
    assert seen["argv"] == ["Which customers renew in Q3?"]

    # Reserved-but-not-yet-shipped subcommands say so and exit 2.
    assert front_door.main(["smoke", "acme/widgets"]) == 2
    assert front_door.main(["ingest", "./some-dir"]) == 2

    # `ask` on an unconnected target routes to the connect CLI's honest error.
    assert front_door.main(["ask", "nobody/nothing", "Why did run 1 fail?"]) == 2
