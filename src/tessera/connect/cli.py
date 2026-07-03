"""The BYO subcommands behind the ``tessera`` front door (spec 0118).

    uv run tessera connect github <owner>/<repo>   # fetch a scrubbed snapshot
    uv run tessera ask <owner>/<repo> "<question>"  # answer over it, offline

``connect`` is the network moment (dev-time, bounded, optional no-scope
token); ``ask`` reads only the local workspace and answers with the same
claim-level provenance, routing transparency, and honest refusals as every
other Tessera door.
"""

from __future__ import annotations

import argparse
import sys

from tessera.connect.github import ConnectError, FetchCaps, fetch_snapshot
from tessera.connect.workspace import (
    CONNECT_ROOT,
    WorkspaceNotConnected,
    answer_workspace,
    build_workspace_graph,
    build_workspace_kb,
    load_workspace,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera",
        description=(
            "Bring-your-own-data doors: connect a public GitHub repository, "
            "then ask grounded questions over the local snapshot — offline, "
            "every claim carrying provenance."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser(
        "connect", help="fetch a bounded, scrubbed snapshot of a data source"
    )
    connectors = connect.add_subparsers(dest="connector", required=True)
    github = connectors.add_parser(
        "github", help="a public GitHub repository's Actions history"
    )
    github.add_argument("target", help="<owner>/<repo>, e.g. astral-sh/uv")
    github.add_argument(
        "--runs",
        type=int,
        default=30,
        help="how many recent runs to consider (default 30)",
    )
    github.add_argument(
        "--failed",
        type=int,
        default=5,
        help="failed runs to fetch logs for (default 5)",
    )
    github.add_argument(
        "--jobs-per-run",
        type=int,
        default=3,
        help="failed jobs per run to fetch logs for (default 3)",
    )

    ask = sub.add_parser(
        "ask", help="answer a question over a connected snapshot, offline"
    )
    ask.add_argument("target", help="<owner>/<repo> of a connected repository")
    ask.add_argument("question", help='e.g. "Why did run 28641345176 fail?"')

    args = parser.parse_args(argv)
    if args.command == "connect":
        return _connect(args)
    return _ask(args)


def _connect(args: argparse.Namespace) -> int:
    caps = FetchCaps(
        runs=args.runs, failed_logs=args.failed, jobs_per_run=args.jobs_per_run
    )
    try:
        result = fetch_snapshot(args.target, CONNECT_ROOT, caps=caps)
    except ConnectError as error:
        print(f"connect: {error}", file=sys.stderr)
        return 1

    manifest = result.manifest
    print(
        f"Connected github.com/{args.target} → {result.workspace}/ "
        f"(snapshot {manifest['snapshot_date']})"
    )
    print(
        f"  runs kept: {len(manifest['fetched_run_ids'])} "
        f"(failed with logs: {len(manifest['failed_run_ids_with_logs'])}, "
        f"omitted failed: {len(manifest['omitted_failed_run_ids'])}, "
        f"excluded: {len(manifest['excluded_runs'])})"
    )
    print(
        f"  PRs: {len(manifest['pr_numbers'])} · "
        f"requests: {manifest['request_count']} · "
        f"token: {'yes' if manifest['token_used'] else 'no'}"
    )
    scrubs = manifest["scrub_counts"]
    if scrubs:
        details = ", ".join(f"{name} ×{count}" for name, count in scrubs.items())
        print(f"  scrubbed before disk: {details}")
    for miss in manifest["misses"]:
        print(f"  miss: {miss}")
    if result.metadata_only:
        print(
            "  NOTE: metadata-only snapshot (no failed-run logs) — RCA grounds "
            "on run rows; see the misses above for why."
        )
    if result.suggested_run:
        print(
            f"\nTry: uv run tessera ask {args.target} "
            f'"Why did run {result.suggested_run} fail?"'
        )
    return 0


def _ask(args: argparse.Namespace) -> int:
    try:
        workspace = load_workspace(args.target)
    except WorkspaceNotConnected as error:
        print(f"ask: {error}", file=sys.stderr)
        return 2
    graph = build_workspace_graph(workspace)
    kb = build_workspace_kb(workspace)
    route, answer = answer_workspace(args.question, graph, kb)
    print(
        f"[connect:{workspace.name} (github.com/{workspace.repo}, "
        f"snapshot {workspace.snapshot_date}) · route: {route.kind} — "
        f"{route.reason}]"
    )
    print(answer.render())
    return 0
