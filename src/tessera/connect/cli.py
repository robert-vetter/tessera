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
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.connect.github import ConnectError, FetchCaps, fetch_snapshot
from tessera.connect.workspace import (
    CONNECT_ROOT,
    InvalidTarget,
    WorkspaceNotConnected,
    answer_workspace,
    build_workspace_graph,
    build_workspace_kb,
    load_workspace,
)
from tessera.devex.rca import RUN_ID

if TYPE_CHECKING:
    from tessera.graph import KnowledgeGraph


def _positive(minimum: int, maximum: int | None = None) -> Callable[[str], int]:
    """An argparse type that rejects out-of-range integers with a clear message."""

    def check(raw: str) -> int:
        value = int(raw)
        if value < minimum or (maximum is not None and value > maximum):
            bound = f"{minimum}..{maximum}" if maximum is not None else f">= {minimum}"
            raise argparse.ArgumentTypeError(f"must be {bound}, got {value}")
        return value

    return check


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
        type=_positive(1, 100),
        default=30,
        help="how many recent runs to consider, 1..100 (default 30)",
    )
    github.add_argument(
        "--failed",
        type=_positive(0),
        default=5,
        help="failed runs to fetch logs for (default 5)",
    )
    github.add_argument(
        "--jobs-per-run",
        type=_positive(0),
        default=3,
        help="failed jobs per run to fetch logs for (default 3)",
    )

    ask = sub.add_parser(
        "ask", help="answer a question over a connected snapshot, offline"
    )
    ask.add_argument("target", help="<owner>/<repo> of a connected repository")
    ask.add_argument("question", help='e.g. "Why did run 28641345176 fail?"')

    smoke = sub.add_parser(
        "smoke", help="check the trust contract holds on a connected snapshot"
    )
    smoke.add_argument("target", help="<owner>/<repo> of a connected repository")

    ingest = sub.add_parser(
        "ingest", help="ingest a local CSV + Markdown directory (tessera.toml)"
    )
    ingest.add_argument("directory", help="a directory containing a tessera.toml")
    ingest.add_argument(
        "question", nargs="?", help="optional: also answer this over the corpus"
    )

    args = parser.parse_args(argv)
    if args.command == "connect":
        return _connect(args)
    if args.command == "smoke":
        return _smoke(args)
    if args.command == "ingest":
        return _ingest(args)
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
    if result.metadata_only and result.metadata_only_reason:
        print(
            "  NOTE: no failed-run logs in this snapshot — "
            f"{result.metadata_only_reason}."
        )
    if result.suggested_run:
        print(
            f"\nTry: uv run tessera ask {args.target} "
            f'"Why did run {result.suggested_run} fail?"'
        )
    return 0


def _ask(args: argparse.Namespace) -> int:
    # A target that is a local directory with a tessera.toml is an ingested
    # corpus (Unit 4); anything else is a connected GitHub workspace. This is
    # unambiguous — an <owner>/<repo> is not a local directory.
    if _is_ingest_dir(args.target):
        return _ask_dir(args.target, args.question)

    try:
        workspace = load_workspace(args.target)
    except (InvalidTarget, WorkspaceNotConnected) as error:
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
    if not answer.is_grounded:
        pointer = _manifest_pointer(args.question, workspace.manifest)
        if pointer:
            print(f"\n{pointer}")
    return 0


def _is_ingest_dir(target: str) -> bool:
    from tessera.ingest.config import CONFIG_NAME

    return (Path(target) / CONFIG_NAME).is_file()


def _ingest(args: argparse.Namespace) -> int:
    from tessera.ingest.config import IngestConfigError, load_config
    from tessera.ingest.source import DirSource, build_dir_graph

    try:
        config = load_config(Path(args.directory))
        source = DirSource(config)
        records = source.ingest()
        graph = build_dir_graph(config)
    except IngestConfigError as error:
        print(f"ingest: {error}", file=sys.stderr)
        return 1

    table_records = [r for r in records if r.origin.locator.kind != "doc-span"]
    doc_records = [r for r in records if r.origin.locator.kind == "doc-span"]
    clusters = graph.clusters()
    merged = [c for c in clusters if len(c) > 1]
    ambiguous = _ambiguous_names(graph, source.display_names())

    print(f"Ingested {config.name} ({config.root}):")
    print(
        f"  {len(table_records)} table row(s) across {len(config.tables)} table(s); "
        f"{len(doc_records)} document chunk(s)."
    )
    print(
        f"  entity resolution: {len(clusters)} resolved entities "
        f"({len(merged)} multi-node merge(s)); "
        f"{len(graph.mentions)} document mention(s)."
    )
    if ambiguous:
        for name, count in ambiguous:
            print(
                f"  ambiguous name: '{name}' → {count} distinct entities (asks refuse)"
            )
    if args.question:
        print()
        return _ask_dir(args.directory, args.question)
    print(f'\nTry: uv run tessera ask {args.directory} "<question>"')
    return 0


def _ask_dir(directory: str, question: str | None) -> int:
    from tessera.ingest.answer import answer_dir
    from tessera.ingest.config import IngestConfigError, load_config
    from tessera.ingest.source import DirSource, build_dir_graph, build_dir_kb

    if not question:
        print("ask: a question is required.", file=sys.stderr)
        return 2
    try:
        config = load_config(Path(directory))
        source = DirSource(config)
        graph = build_dir_graph(config)
        kb = build_dir_kb(config)
    except IngestConfigError as error:
        print(f"ask: {error}", file=sys.stderr)
        return 1
    route, answer = answer_dir(question, graph, kb, source.display_names())
    print(f"[ingest:{config.name} · route: {route.kind} — {route.reason}]")
    print(answer.render())
    return 0


def _ambiguous_names(
    graph: KnowledgeGraph, display_names: set[str]
) -> list[tuple[str, int]]:
    from tessera.ingest.answer import name_nodes_for

    out: list[tuple[str, int]] = []
    for name in sorted(display_names):
        nodes = name_nodes_for(graph, name)
        components = {graph.entity_of(node.id) for node in nodes}
        if len(components) > 1:
            out.append((name, len(components)))
    return out


def _smoke(args: argparse.Namespace) -> int:
    from tessera.connect.smoke import run_smoke

    try:
        workspace = load_workspace(args.target)
    except (InvalidTarget, WorkspaceNotConnected) as error:
        print(f"smoke: {error}", file=sys.stderr)
        return 2
    report = run_smoke(workspace)
    print(report.render())
    return 0 if report.ok else 1


def _manifest_pointer(question: str, manifest: Mapping[str, object]) -> str | None:
    """If a refused run id is in the snapshot's omitted/excluded lists, say so —
    "no run X" then reads as "not in this snapshot", not "never existed"."""
    match = RUN_ID.search(question)
    if not match:
        return None
    run_id = match.group(0)
    if not run_id.isdigit():
        return None
    run_int = int(run_id)
    omitted = manifest.get("omitted_failed_run_ids")
    if isinstance(omitted, list) and run_int in omitted:
        return (
            f"(run {run_id} is a failed run this snapshot omitted under the "
            "--failed cap — raise --failed and re-connect to include it.)"
        )
    excluded = manifest.get("excluded_runs")
    if isinstance(excluded, dict) and run_id in excluded:
        return (
            f"(run {run_id} was excluded at connect time: {excluded[run_id]} — "
            "not a completed success/failure.)"
        )
    return None
