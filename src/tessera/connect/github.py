"""Fetch a bounded, scrubbed GitHub Actions snapshot of any public repository.

The network moment of the BYO door (spec 0118, ADR 0028): ``tessera connect
github <owner>/<repo>`` calls this module **once, at dev time**; everything
downstream (graph, RCA, provenance) reads only the files written here. The
snapshot lands in the exact on-disk format of the committed ADR 0014 corpus
— ``runs/<id>.json`` in the gh-CLI field shape, ``logs/<id>.failed.log`` in
the TSV ``job⇥step⇥<timestamp> <message>`` shape — so the existing
:class:`tessera.sources.github_actions.GitHubActionsSource` reads a foreign
workspace with zero change.

Honesty mechanics, all recorded in the workspace ``MANIFEST.json``:

- **Bounded fetch** (spec 0117 decision 7): explicit caps on runs, failed-run
  logs, jobs per run, job-listing pages, and log bytes. Whatever a cap
  excludes is a **named miss**, never silence.
- **Scrub before disk** (decision 6): every byte written passes
  :mod:`tessera.connect.scrub`; per-pattern counts land in the manifest.
- **Auth posture** (decision 3, measured): metadata is anonymous; log content
  needs the optional classic no-scope ``GITHUB_TOKEN``. The token is read
  from the environment only, reported as a boolean only, and sent **only**
  to ``api.github.com`` — GitHub redirects log downloads to signed blob
  storage, and this module follows those redirects manually so the auth
  header never travels to the redirect target (urllib would forward it).
- **Only completed passed/failed runs** enter the snapshot: those are the two
  outcomes the RCA vocabulary speaks truthfully (a refusal says "did not
  fail — it passed"); in-progress/cancelled/skipped runs are excluded by id
  in the manifest.

Determinism boundary: fetching is wall-clock, network work (like
``scripts/fetch_github_actions_snapshot.py``); the *snapshot* pins run ids +
date, and answering over it is deterministic and offline (ADR 0014/0028).
"""

from __future__ import annotations

import http.client
import json
import os
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tessera.connect.scrub import (
    merge_counts,
    neutralize_controls,
    scrub_json_values,
    scrub_line,
    scrub_text,
)

JsonObj = dict[str, Any]

API_ROOT = "https://api.github.com"
_API_HOST = "api.github.com"
_API_VERSION = "2022-11-28"
_USER_AGENT = "tessera-connect (https://github.com/robert-vetter/tessera)"

# <owner>/<repo>, both segments GitHub-legal (no slashes, no whitespace).
TARGET = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

# A runner-log line starts "2026-07-02T17:11:47.0264047Z ..."; windows compare
# on the second-precision prefix because the jobs API reports seconds.
_LINE_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_TS_PRECISION = 19  # len("2026-07-02T17:11:47")

# Hard ceiling for any single HTTP body. Tail-keeping a log needs the full
# text, so a log larger than this is skipped with a named miss instead.
_READ_CEILING = 25 * 1024 * 1024
_MAX_REDIRECTS = 4
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


@dataclass(frozen=True)
class FetchCaps:
    """The bounded-fetch knobs (spec 0118 decision 5). Defaults are the record."""

    runs: int = 30
    failed_logs: int = 5
    jobs_per_run: int = 3
    job_pages: int = 3
    prs: int = 30
    pr_body_chars: int = 500
    log_bytes: int = 2 * 1024 * 1024

    def as_manifest(self) -> JsonObj:
        return {
            "runs": self.runs,
            "failed_logs": self.failed_logs,
            "jobs_per_run": self.jobs_per_run,
            "job_pages": self.job_pages,
            "prs": self.prs,
            "pr_body_chars": self.pr_body_chars,
            "log_bytes": self.log_bytes,
        }


# The recorded defaults (frozen, shareable — spec 0118 decision 5).
DEFAULT_CAPS = FetchCaps()


@dataclass(frozen=True)
class FetchResponse:
    """One HTTP exchange as the fetcher sees it (transport-agnostic)."""

    status: int
    headers: Mapping[str, str]  # lower-cased keys
    body: bytes
    truncated: bool = False  # body hit the read ceiling


# A transport takes (url, headers) and returns the response WITHOUT following
# redirects — redirect policy (and the auth-header hygiene it implies) is the
# fetcher's job, not the transport's. Tests inject a fake; the default wraps
# urllib with redirects disabled.
Transport = Callable[[str, Mapping[str, str]], FetchResponse]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    """An opener that speaks ONLY http/https and never redirects.

    Built by hand rather than via ``build_opener`` so it carries no
    ``FileHandler``/``FTPHandler``/``DataHandler`` — a hostile ``Location``
    header pointing at ``file://`` or ``data:`` has nothing to open even if
    the scheme guard in ``_Fetch.request`` were bypassed (defense in depth;
    the guard is the primary control). ``HTTPErrorProcessor`` keeps the
    4xx/5xx-as-``HTTPError`` behaviour the transport turns into a response.
    """
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.ProxyHandler(),
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(),
        urllib.request.HTTPErrorProcessor(),
        urllib.request.HTTPDefaultErrorHandler(),
        # Turns any non-http(s) scheme (file://, ftp://, data:) into a clean
        # URLError instead of a None-open — nothing to exfiltrate, and the
        # transport maps that URLError to a ConnectError.
        urllib.request.UnknownHandler(),
        _NoRedirect(),
    ):
        opener.add_handler(handler)
    return opener


_OPENER = _build_opener()


class ConnectError(Exception):
    """A fetch problem with a message meant for the user, verbatim."""


def default_transport(url: str, headers: Mapping[str, str]) -> FetchResponse:
    """The real network call: one request, no redirect following, capped read.

    Every non-HTTP failure (DNS, timeout, TLS, connection reset — the most
    common way a fetch goes wrong) becomes a :class:`ConnectError` with a
    clean message, never a raw traceback (spec 0118 acceptance criterion).
    """
    request = urllib.request.Request(url, headers=dict(headers))
    try:
        with _OPENER.open(request, timeout=30) as response:
            body = response.read(_READ_CEILING + 1)
            return FetchResponse(
                status=response.status,
                headers={k.lower(): v for k, v in response.headers.items()},
                body=body[:_READ_CEILING],
                truncated=len(body) > _READ_CEILING,
            )
    except urllib.error.HTTPError as error:  # 4xx/5xx — a response, not a crash
        return FetchResponse(
            status=error.code,
            headers={k.lower(): v for k, v in error.headers.items()},
            body=error.read(),
        )
    except (urllib.error.URLError, OSError, http.client.HTTPException) as error:
        reason = getattr(error, "reason", error)
        raise ConnectError(f"network error fetching {url}: {reason}") from error


@dataclass
class SnapshotResult:
    """What ``connect`` reports: where the snapshot is and what it holds."""

    workspace: Path
    manifest: JsonObj
    suggested_run: str | None  # a real failed run id with a log, for the demo ask
    metadata_only: bool
    metadata_only_reason: str | None = None


@dataclass
class _Fetch:
    """One snapshot fetch: client state, tallies, and the manifest-to-be."""

    transport: Transport
    token: str | None
    requests_made: int = 0
    misses: list[str] = field(default_factory=list)
    scrub_counts: dict[str, int] = field(default_factory=dict)
    logs_available: bool = True

    # --- HTTP ------------------------------------------------------------------
    def _headers(self, url: str) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _API_VERSION,
            "User-Agent": _USER_AGENT,
        }
        # The token goes to api.github.com over HTTPS and nowhere else (spec
        # 0118 decision 3): a redirect target (GitHub's signed blob host) never
        # sees it, and a scheme-downgrade redirect to http://api.github.com
        # cannot carry it in cleartext.
        parsed = urllib.parse.urlparse(url)
        if self.token and parsed.scheme == "https" and parsed.netloc == _API_HOST:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, url: str) -> FetchResponse:
        """GET with manual redirect handling and the auth-hygiene rule."""
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            self.requests_made += 1
            response = self.transport(current, self._headers(current))
            if response.status in _REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise ConnectError(
                        f"GitHub answered {response.status} without a Location "
                        f"header for {current}"
                    )
                # Resolve relative targets against the current URL, and follow
                # only http(s) — never file://, ftp://, data:, etc.
                current = urllib.parse.urljoin(current, location)
                scheme = urllib.parse.urlparse(current).scheme.lower()
                if scheme not in ("http", "https"):
                    raise ConnectError(
                        f"refusing to follow a non-http redirect to {current!r}"
                    )
                continue
            return response
        raise ConnectError(f"too many redirects fetching {url}")

    def get_json(self, url: str, *, context: str) -> JsonObj:
        response = self.request(url)
        if response.status != 200:
            raise self._error(response, context)
        try:
            parsed = json.loads(response.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ConnectError(
                f"{context}: GitHub returned a 200 that is not JSON "
                "(a captive portal or proxy may be intercepting the request)."
            ) from error
        if not isinstance(parsed, dict):
            raise ConnectError(f"{context}: unexpected JSON shape from GitHub.")
        return parsed

    def _error(self, response: FetchResponse, context: str) -> ConnectError:
        if response.status == 404:
            return ConnectError(
                f"{context}: GitHub returned 404 — the repository does not "
                "exist, is private, or has no such resource."
            )
        if response.status == 401:
            return ConnectError(
                f"{context}: GitHub returned 401 — if GITHUB_TOKEN is set it is "
                "invalid, expired, or revoked; unset it to fetch anonymously."
            )
        if response.status in (403, 429):
            if response.headers.get("x-ratelimit-remaining") == "0":
                reset = _reset_time(response.headers.get("x-ratelimit-reset"))
                hint = (
                    "wait, or add the optional no-scope GITHUB_TOKEN to your "
                    "environment (see .env.example)"
                    if self.token is None
                    else "wait for the reset"
                )
                return ConnectError(
                    f"{context}: GitHub rate limit exhausted (resets {reset}) — {hint}."
                )
            if response.headers.get("retry-after"):
                return ConnectError(
                    f"{context}: GitHub secondary rate limit "
                    f"(retry after {response.headers['retry-after']}s)."
                )
            return ConnectError(
                f"{context}: GitHub returned {response.status} (forbidden)."
            )
        return ConnectError(f"{context}: GitHub returned {response.status}.")

    # --- log download (the token-gated, redirect-following call) ----------------
    def get_job_log(self, owner: str, repo: str, job: JsonObj) -> str | None:
        """The raw log text of one job, or None with a named reason.

        A 403 that is not a rate limit means log access is closed to this
        caller (no token — the measured anonymous behaviour); that verdict is
        cached so a token-less connect probes once, not once per job.
        """
        if not self.logs_available:
            return None
        job_id, job_name = job["id"], str(job.get("name", ""))
        url = f"{API_ROOT}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
        response = self.request(url)
        if response.status == 200:
            if response.truncated:
                self.misses.append(
                    f"job '{job_name}' ({job_id}): log larger than the "
                    f"{_READ_CEILING // (1024 * 1024)} MiB read ceiling — skipped."
                )
                return None
            return response.body.decode("utf-8", errors="replace")
        if response.status == 404:
            self.misses.append(
                f"job '{job_name}' ({job_id}): log absent on GitHub "
                "(expired or never produced)."
            )
            return None
        if response.status in (401, 403, 429):
            if response.headers.get("x-ratelimit-remaining") == "0" or (
                response.status in (403, 429) and response.headers.get("retry-after")
            ):
                raise self._error(response, f"log of job {job_id}")
            self.logs_available = False
            if self.token is None:
                self.misses.append(
                    "failed-run logs skipped: GitHub requires authentication for "
                    "log content even on public repositories (measured; spec 0117 "
                    "decision 3) — add the optional no-scope GITHUB_TOKEN to fetch "
                    "logs."
                )
            else:
                self.misses.append(
                    f"failed-run logs skipped: the provided GITHUB_TOKEN was not "
                    f"accepted for log content (HTTP {response.status}) — check the "
                    "token (a fine-grained PAT needs no scopes for public repos; a "
                    "classic token must be SSO-authorized for the org)."
                )
            return None
        raise self._error(response, f"log of job {job_id}")


def fetch_snapshot(
    target: str,
    root: Path,
    *,
    caps: FetchCaps = DEFAULT_CAPS,
    token: str | None = None,
    transport: Transport | None = None,
    snapshot_date: str | None = None,
    fetched_at: str | None = None,
) -> SnapshotResult:
    """Fetch ``owner/repo`` into ``root/<owner>-<repo>/`` and pin the manifest.

    ``token`` defaults to ``GITHUB_TOKEN`` from the environment — deliberately
    never ``TESSERA_GITHUB_TOKEN`` (the actuator's RW credential stays off
    read paths, spec 0118 decision 4). The workspace replaces any previous
    snapshot of the same repo via move-aside-then-swap; a failed fetch (all
    network work precedes the first write) leaves it untouched.
    """
    if not TARGET.match(target):
        raise ConnectError(
            f"'{target}' is not an <owner>/<repo> target (e.g. astral-sh/uv)."
        )
    owner, repo = target.split("/", 1)
    if transport is None:
        transport = default_transport
    if token is None:
        token = os.environ.get("GITHUB_TOKEN") or None
    now = datetime.now(UTC)
    if fetched_at is None:
        fetched_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if snapshot_date is None:
        snapshot_date = fetched_at[:10]

    fetch = _Fetch(transport=transport, token=token)
    if token is None:
        fetch.logs_available = False
        fetch.misses.append(
            "no GITHUB_TOKEN in the environment: metadata-only snapshot "
            "(GitHub requires authentication for log content even on public "
            "repositories — measured 2026-07-03). The optional classic "
            "no-scope token in .env unlocks failed-run logs."
        )

    # 1) The recent-runs listing (anonymous-capable). GitHub caps per_page at
    #    100 and we fetch one page, so the effective request is min(runs, 100).
    per_page = min(caps.runs, 100)
    listing = fetch.get_json(
        f"{API_ROOT}/repos/{owner}/{repo}/actions/runs?per_page={per_page}",
        context=f"workflow runs of {target}",
    )
    total_run_count = int(listing.get("total_count") or 0)
    runs_raw = list(listing.get("workflow_runs") or [])
    if caps.runs > 100:
        fetch.misses.append(
            f"--runs {caps.runs} exceeds GitHub's 100-per-page maximum for a "
            "single page; considered the 100 most recent runs."
        )
    if total_run_count > len(runs_raw):
        fetch.misses.append(
            f"considered the {len(runs_raw)} most recent of {total_run_count} "
            "total runs (one page); older failures are outside this snapshot."
        )
    kept: list[JsonObj] = []
    excluded: dict[str, str] = {}
    for raw in runs_raw:
        if raw.get("id") is None:
            continue  # a listing entry with no id can't be cited — skip it
        conclusion = raw.get("conclusion")
        if raw.get("status") == "completed" and conclusion in ("success", "failure"):
            kept.append(_map_run(raw))
        else:
            excluded[str(raw.get("id"))] = str(conclusion or raw.get("status") or "?")
    if excluded:
        fetch.misses.append(
            f"{len(excluded)} of the {len(runs_raw)} most recent runs excluded "
            "(not completed as success/failure — see excluded_runs)."
        )

    failed = [r for r in kept if r["conclusion"] == "failure"]
    failed.sort(key=lambda r: (str(r["createdAt"]), str(r["databaseId"])), reverse=True)
    with_logs = failed[: caps.failed_logs]
    omitted = failed[caps.failed_logs :]
    if omitted:
        fetch.misses.append(
            f"{len(omitted)} failed run(s) beyond the --failed cap "
            f"({caps.failed_logs}) omitted from the snapshot entirely "
            "(see omitted_failed_run_ids)."
        )
    with_logs_ids = {r["databaseId"] for r in with_logs}
    written_runs = [
        r
        for r in kept
        if r["conclusion"] != "failure" or r["databaseId"] in with_logs_ids
    ]

    # 2) Jobs + failed-step logs for the selected failed runs.
    logs_tsv: dict[str, str] = {}
    for run in with_logs:
        run_id = str(run["databaseId"])
        jobs = _fetch_jobs(fetch, owner, repo, run_id, caps)
        run["jobs"] = [_trim_job(j) for j in jobs]
        failed_jobs = [j for j in jobs if j.get("conclusion") == "failure"]
        if len(failed_jobs) > caps.jobs_per_run:
            fetch.misses.append(
                f"run {run_id}: {len(failed_jobs)} failed jobs, logs fetched "
                f"for the first {caps.jobs_per_run} (--jobs-per-run cap)."
            )
            failed_jobs = failed_jobs[: caps.jobs_per_run]
        tsv_lines: list[str] = []
        for job in failed_jobs:
            log_text = fetch.get_job_log(owner, repo, job)
            if log_text is None:
                continue
            log_text = _cap_log_tail(
                log_text,
                caps.log_bytes,
                fetch.misses,
                label=f"run {run_id} job '{_tsv_field(str(job.get('name', '')))}'",
            )
            tsv_lines.extend(_failed_step_tsv(run_id, job, log_text, fetch.misses))
        if tsv_lines:
            logs_tsv[run_id] = "\n".join(tsv_lines) + "\n"

    # 3) One page of recent PRs — the "if cheap" extra (spec 0118 decision 5).
    prs: list[JsonObj] = []
    if caps.prs > 0:
        pr_listing = fetch.request(
            f"{API_ROOT}/repos/{owner}/{repo}/pulls"
            f"?state=all&per_page={min(caps.prs, 100)}&sort=created&direction=desc"
        )
        if pr_listing.status == 200:
            try:
                raw_prs = json.loads(pr_listing.body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                raw_prs = []
                fetch.misses.append("pull requests skipped: GitHub reply was not JSON.")
            prs = [
                _map_pr(raw)
                for raw in raw_prs
                if isinstance(raw, dict) and raw.get("number") is not None
            ]
        else:
            fetch.misses.append(
                f"pull requests skipped: GitHub returned {pr_listing.status}."
            )

    # 4) Write everything — scrubbed — into a temp dir, then swap into place.
    workspace = root / f"{owner}-{repo}".lower()
    manifest: JsonObj = {
        "dataset": "github_connect",
        "synthetic": False,
        "repo": target,
        "snapshot_date": snapshot_date,
        "fetched_at": fetched_at,
        "api_version": _API_VERSION,
        "fetched_by": "tessera connect github (tessera.connect.github)",
        "token_used": token is not None,
        "request_count": fetch.requests_made,
        "caps": caps.as_manifest(),
        "total_run_count": total_run_count,
        "fetched_run_ids": sorted(int(r["databaseId"]) for r in written_runs),
        "failed_run_ids_with_logs": sorted(int(i) for i in logs_tsv),
        "omitted_failed_run_ids": sorted(int(r["databaseId"]) for r in omitted),
        "excluded_runs": dict(sorted(excluded.items())),
        "pr_numbers": sorted(int(p["number"]) for p in prs),
        "scrub_counts": {},  # filled by _write_workspace
        "misses": list(fetch.misses),
    }
    _write_workspace(
        workspace, written_runs, logs_tsv, prs, manifest, fetch, caps.pr_body_chars
    )

    # A failed run with a usable log grounds the demo ask; if none, the run row
    # still grounds a one-claim RCA (metadata-only). Distinguish "no failed
    # runs at all" from "logs were unavailable" so the CLI reports honestly.
    suggested = None
    if logs_tsv:
        suggested = max(logs_tsv, key=int)
    elif with_logs:
        suggested = str(with_logs[0]["databaseId"])
    if logs_tsv:
        reason = None
    elif not failed:
        reason = "no failed runs among the runs considered"
    else:
        reason = "failed-run logs were unavailable (see misses)"
    return SnapshotResult(
        workspace=workspace,
        manifest=manifest,
        suggested_run=suggested,
        metadata_only=not logs_tsv,
        metadata_only_reason=reason,
    )


# --- fetch helpers -----------------------------------------------------------------
def _fetch_jobs(
    fetch: _Fetch, owner: str, repo: str, run_id: str, caps: FetchCaps
) -> list[JsonObj]:
    """All jobs of a run, paged, capped at ``caps.job_pages`` (a named miss)."""
    jobs: list[JsonObj] = []
    total = 0
    for page in range(1, caps.job_pages + 1):
        data = fetch.get_json(
            f"{API_ROOT}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
            f"?per_page=100&page={page}",
            context=f"jobs of run {run_id}",
        )
        batch = list(data.get("jobs") or [])
        total = int(data.get("total_count") or 0)
        jobs.extend(batch)
        if len(batch) < 100:
            return jobs
    if total > len(jobs):
        fetch.misses.append(
            f"run {run_id}: {total} jobs, listing capped at {len(jobs)} "
            f"({caps.job_pages} pages) — failed jobs beyond the cap are "
            "invisible to this snapshot."
        )
    return jobs


def _tsv_field(value: str) -> str:
    """A job/step name safe as a TSV column: no tab/newline/control chars.

    A tab or newline in a foreign workflow's job/step name (both are legal in
    GitHub YAML, especially ``fromJSON`` matrix expansions) would shift the
    ``job⇥step⇥message`` columns the parser splits on and mis-attribute a
    locator to a job/step that does not exist. Neutralized at synthesis, since
    the whole-TSV scrub downstream deliberately preserves structural tabs.
    """
    cleaned, _ = neutralize_controls(value)
    return cleaned.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _cap_log_tail(text: str, cap_bytes: int, misses: list[str], *, label: str) -> str:
    """Keep the tail of an oversized log (errors live at the end) — named."""
    if len(text.encode("utf-8", errors="replace")) <= cap_bytes:
        return text
    lines = text.splitlines()
    kept: list[str] = []
    size = 0
    for line in reversed(lines):
        size += len(line.encode("utf-8", errors="replace")) + 1
        if size > cap_bytes:
            break
        kept.append(line)
    kept.reverse()
    if kept:
        misses.append(
            f"{label}: log truncated to its last {len(kept)} of {len(lines)} "
            f"lines ({cap_bytes // (1024 * 1024)} MiB cap)."
        )
    else:
        # A single line exceeds the cap — nothing citable survives.
        misses.append(
            f"{label}: a single log line exceeds the {cap_bytes // (1024 * 1024)} "
            "MiB cap — no log kept for this job."
        )
    return "\n".join(kept)


def _failed_step_tsv(
    run_id: str, job: JsonObj, log_text: str, misses: list[str]
) -> list[str]:
    """Synthesize the gh-CLI ``job⇥step⇥line`` TSV for a job's failed steps.

    Lines are attributed to a step by the jobs API's per-step
    ``started_at``/``completed_at`` window (second precision, inclusive);
    a failed step without a usable window falls back to the whole job log
    with an empty step column — and a named miss (spec 0118 decision 1).

    Measured characteristic (both proof corpora, 2026-07-03): GitHub's step
    timestamps are second-coarse, so a neighbouring step's lines that share
    the boundary second ride into the window carrying the failed step's name
    in the TSV step column — i.e. a ``log-span`` locator can name the failed
    step for a line that actually belongs to the adjacent one (e.g. post-job
    cleanup starting the same second the failed step ended). Inclusive
    boundaries are the deliberate trade: over-labelling a few boundary lines
    beats *losing* the error line to an exclusive boundary. When the boundary
    second is shared, a per-run miss records it so the mislabel is visible in
    the audit artifact, not just the spec.
    """
    job_name = _tsv_field(str(job.get("name", "")))
    lines = log_text.lstrip("﻿").splitlines()
    failed_steps = [
        s for s in (job.get("steps") or []) if s.get("conclusion") == "failure"
    ]
    if not failed_steps:
        kept = "no lines" if not lines else f"{len(lines)} lines"
        misses.append(
            f"run {run_id} job '{job_name}': failed at job level (no failed step "
            f"in the jobs listing) — job log kept without step attribution "
            f"({kept})."
        )
        return [f"{job_name}\t\t{line}" for line in lines]

    out: list[str] = []
    for step in failed_steps:
        step_name = _tsv_field(str(step.get("name", "")))
        start = str(step.get("started_at") or "")[:_TS_PRECISION]
        end = str(step.get("completed_at") or "")[:_TS_PRECISION]
        window = _window_lines(lines, start, end) if start and end else []
        if not window:
            kept = "no lines" if not lines else f"{len(lines)} lines"
            misses.append(
                f"run {run_id} job '{job_name}' step '{step_name}': no usable "
                f"timestamp window — job log kept without step attribution "
                f"({kept})."
            )
            return [f"{job_name}\t\t{line}" for line in lines]
        if _shares_boundary_second(step, job):
            misses.append(
                f"run {run_id} job '{job_name}' step '{step_name}': shares its "
                "start/end second with an adjacent step, so a boundary line may "
                "carry this step's label though it belongs to the neighbour "
                "(inclusive second-precision windows)."
            )
        out.extend(f"{job_name}\t{step_name}\t{line}" for line in window)
    return out


def _shares_boundary_second(step: JsonObj, job: JsonObj) -> bool:
    """True if another step of the job starts or ends in this step's boundary
    second — the condition under which inclusive windows over-label a line."""
    start = str(step.get("started_at") or "")[:_TS_PRECISION]
    end = str(step.get("completed_at") or "")[:_TS_PRECISION]
    for other in job.get("steps") or []:
        if other is step:
            continue
        o_start = str(other.get("started_at") or "")[:_TS_PRECISION]
        o_end = str(other.get("completed_at") or "")[:_TS_PRECISION]
        if o_start and o_start in (start, end):
            return True
        if o_end and o_end in (start, end):
            return True
    return False


def _window_lines(lines: list[str], start: str, end: str) -> list[str]:
    """The log lines whose timestamps fall in [start, end]; untimestamped
    continuation lines belong to the window of the last timestamped line."""
    selected: list[str] = []
    inside = False
    for line in lines:
        match = _LINE_TS.match(line)
        if match:
            inside = start <= match.group(0) <= end
        if inside:
            selected.append(line)
    return selected


# --- shape mapping (REST field names → the committed-snapshot shape) ---------------
def _map_run(raw: JsonObj) -> JsonObj:
    return {
        "databaseId": raw["id"],
        "workflowName": str(raw.get("name") or ""),
        "displayTitle": str(raw.get("display_title") or ""),
        "headBranch": str(raw.get("head_branch") or ""),
        "headSha": str(raw.get("head_sha") or ""),
        "event": str(raw.get("event") or ""),
        "conclusion": str(raw.get("conclusion") or ""),
        "createdAt": str(raw.get("created_at") or ""),
        "jobs": [],
    }


def _trim_job(job: JsonObj) -> JsonObj:
    """The run/job/step shape the source needs — the fetch script's trim."""
    return {
        "name": str(job.get("name") or ""),
        "conclusion": str(job.get("conclusion") or ""),
        "status": str(job.get("status") or ""),
        "steps": [
            {
                "number": step.get("number"),
                "name": str(step.get("name") or ""),
                "conclusion": str(step.get("conclusion") or ""),
            }
            for step in (job.get("steps") or [])
        ],
    }


def _map_pr(raw: JsonObj) -> JsonObj:
    # The full body is kept here; it is scrubbed and THEN size-capped by the
    # writer, so a credential straddling the cap can't dodge scrubbing.
    user = raw.get("user") or {}
    head = raw.get("head") or {}
    base = raw.get("base") or {}
    return {
        "number": raw["number"],
        "title": str(raw.get("title") or ""),
        "state": str(raw.get("state") or ""),
        "author": str(user.get("login") or ""),
        "createdAt": str(raw.get("created_at") or ""),
        "mergedAt": str(raw.get("merged_at") or ""),
        "headRef": str(head.get("ref") or ""),
        "baseRef": str(base.get("ref") or ""),
        "body": str(raw.get("body") or ""),
    }


# --- the writer --------------------------------------------------------------------
def _write_workspace(
    workspace: Path,
    runs: list[JsonObj],
    logs_tsv: dict[str, str],
    prs: list[JsonObj],
    manifest: JsonObj,
    fetch: _Fetch,
    pr_body_chars: int,
) -> None:
    """Scrub everything (including the manifest's own free text), write to a
    temp dir, then swap into place without a window where the old snapshot is
    already gone and the new one is not yet in place."""
    tmp = workspace.parent / f".tmp-{workspace.name}"
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "runs").mkdir(parents=True)
    (tmp / "logs").mkdir()
    (tmp / "prs").mkdir()

    for run in runs:
        scrubbed_run, counts = scrub_json_values(run)
        merge_counts(fetch.scrub_counts, counts)
        path = tmp / "runs" / f"{run['databaseId']}.json"
        path.write_text(
            json.dumps(scrubbed_run, indent=2, sort_keys=True) + "\n", "utf-8"
        )
    for run_id, tsv in logs_tsv.items():
        scrubbed_log, counts = scrub_text(tsv)
        merge_counts(fetch.scrub_counts, counts)
        (tmp / "logs" / f"{run_id}.failed.log").write_text(scrubbed_log, "utf-8")
    truncated_bodies = 0
    for pr in prs:
        scrubbed_pr, counts = scrub_json_values(pr)
        merge_counts(fetch.scrub_counts, counts)
        # Cap the body AFTER scrubbing (so a straddling credential can't dodge
        # the scrubber), marking the cut so a claim never reads as complete.
        assert isinstance(scrubbed_pr, dict)
        body = str(scrubbed_pr.get("body") or "")
        if len(body) > pr_body_chars:
            scrubbed_pr["body"] = body[:pr_body_chars] + " …[truncated]"
            truncated_bodies += 1
        path = tmp / "prs" / f"{pr['number']}.json"
        path.write_text(
            json.dumps(scrubbed_pr, indent=2, sort_keys=True) + "\n", "utf-8"
        )
    if truncated_bodies:
        fetch.misses.append(
            f"{truncated_bodies} PR body(ies) truncated to {pr_body_chars} chars "
            "(marked …[truncated])."
        )

    # The manifest's own free text (miss strings interpolate foreign job/step
    # names; excluded-run values are API enums) is scrubbed too, so NOTHING
    # written to the workspace bypasses the scrubber.
    manifest["scrub_counts"] = dict(sorted(fetch.scrub_counts.items()))
    manifest["misses"] = [scrub_line(miss) for miss in fetch.misses]
    manifest["excluded_runs"] = {
        run_id: scrub_line(value)
        for run_id, value in manifest.get("excluded_runs", {}).items()
    }
    manifest["request_count"] = fetch.requests_made
    (tmp / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8"
    )
    (tmp / "NOTICE").write_text(_notice(manifest), "utf-8")

    # Swap: move any existing snapshot aside, put the new one in, then delete
    # the old — a crash never leaves the target missing (only a stray dir).
    aside = workspace.parent / f".old-{workspace.name}"
    if aside.exists():
        shutil.rmtree(aside)
    if workspace.exists():
        workspace.rename(aside)
    tmp.rename(workspace)
    if aside.exists():
        shutil.rmtree(aside)


def _notice(manifest: JsonObj) -> str:
    return (
        f"Local snapshot of github.com/{manifest['repo']} "
        f"(GitHub Actions runs, failed-step logs, recent PRs), fetched "
        f"{manifest['fetched_at']} by `tessera connect github`.\n"
        "\n"
        "All text belongs to the upstream project and its contributors and is\n"
        "kept here solely as local analysis material for grounded answers with\n"
        "provenance. Do not redistribute this directory; it is gitignored and\n"
        "must never be committed (spec 0117 decision 2 / ADR 0028).\n"
        "Credential-shaped content was scrubbed at fetch time; see\n"
        "MANIFEST.json `scrub_counts` and `misses` for what was changed or\n"
        "left out.\n"
    )


def _reset_time(epoch: str | None) -> str:
    if epoch and epoch.isdigit():
        stamp = datetime.fromtimestamp(int(epoch), tz=UTC)
        return stamp.strftime("%H:%M:%SZ")
    return "soon"
