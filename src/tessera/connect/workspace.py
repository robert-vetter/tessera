"""Read a connected workspace offline: graph, KB, and the routed answer path.

The answer half of the BYO door (spec 0118, ADR 0028). Everything here reads
only the files ``tessera connect github`` wrote under
``var/connect/<owner>-<repo>/`` — no network, no token, deterministic over
the snapshot. The heavy lifting is deliberately **reused, unchanged**: the
existing :class:`~tessera.sources.github_actions.GitHubActionsSource` parses
runs and failed-step logs (the workspace is written in its exact on-disk
format), the engine builds the graph, and the DevEx RCA answers failure
questions. The only new reader is the small PR-row ingester (PRs are a
workspace extra the committed corpus does not have).

Provenance truthfulness: the source module stamps origins with its committed
path prefix (``github_actions/…``); a workspace record's origin is **rebased**
to the real on-disk location (``var/connect/<name>/…``) so every rendered
provenance line points at a file that actually exists there (Pillar 1). Ids
and locators are untouched, so graph mechanics and claim verification behave
identically to the measured battery.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from tessera.devex.rca import RUN_ID, explain_failure
from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import Answer, EvidenceRecord, KnowledgeBase, Locator, Origin
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route
from tessera.sources.github_actions import GitHubActionsSource

JsonObj = dict[str, Any]

# Workspaces live under the invocation directory (documented in PILOT.md):
# foreign snapshots are the *user's* material, not the repo's — and var/ is
# gitignored so they can never be committed (spec 0117 decision 2).
CONNECT_ROOT = Path("var") / "connect"

# The unstructured-chunk locator kinds (mirrors the devex assembly).
_CHUNK_LOCATOR_KINDS = frozenset({"log-span", "diff-hunk"})


class WorkspaceNotConnected(Exception):
    """Raised when a target has no snapshot yet; the message says what to run."""

    def __init__(self, target: str) -> None:
        super().__init__(
            f"no workspace for '{target}' — run "
            f"`uv run tessera connect github {target}` first."
        )


@dataclass(frozen=True)
class Workspace:
    """One connected snapshot: its directory and pinned manifest."""

    name: str  # "<owner>-<repo>", the directory name
    path: Path
    manifest: JsonObj

    @property
    def repo(self) -> str:
        return str(self.manifest.get("repo", self.name))

    @property
    def snapshot_date(self) -> str:
        return str(self.manifest.get("snapshot_date", ""))


def workspace_name(target: str) -> str:
    """``owner/repo`` → the workspace directory name (lowercased)."""
    return target.replace("/", "-").lower()


def load_workspace(target: str, root: Path = CONNECT_ROOT) -> Workspace:
    """Resolve ``owner/repo`` (or a literal workspace dir name) to a workspace."""
    name = workspace_name(target) if "/" in target else target.lower()
    path = root / name
    manifest_path = path / "MANIFEST.json"
    if not manifest_path.is_file():
        raise WorkspaceNotConnected(target)
    manifest: JsonObj = json.loads(manifest_path.read_text("utf-8"))
    return Workspace(name=name, path=path, manifest=manifest)


# --- the PR-row ingester (workspace extra; same door, table-row locators) ----------
@dataclass(frozen=True)
class PRSource:
    """Ingester for the workspace's ``prs/<number>.json`` rows."""

    workspace: Workspace

    def _prs(self) -> list[JsonObj]:
        pr_dir = self.workspace.path / "prs"
        if not pr_dir.is_dir():
            return []
        paths = sorted(pr_dir.glob("*.json"), key=lambda p: int(p.stem))
        return [json.loads(path.read_text("utf-8")) for path in paths]

    def ingest(self) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for row_number, pr in enumerate(self._prs(), start=1):
            number = pr.get("number")
            records.append(
                EvidenceRecord(
                    id=f"PR:{number}",
                    origin=Origin(
                        source=f"var/connect/{self.workspace.name}/prs/{number}.json",
                        locator=Locator.table_row("PR", row_number),
                        ingested_at=self.workspace.snapshot_date,
                    ),
                    text=_pr_text(pr),
                )
            )
        return records


def _pr_text(pr: JsonObj) -> str:
    merged = pr.get("mergedAt") or ""
    state = str(pr.get("state") or "")
    outcome = f"{state}, merged {merged}" if merged else state
    body = str(pr.get("body") or "")
    tail = f" — {body}" if body else ""
    return (
        f'PR #{pr.get("number")} "{pr.get("title", "")}" by {pr.get("author", "")} '
        f"({outcome}): {pr.get('headRef', '')} into {pr.get('baseRef', '')}.{tail}"
    )


# --- records / graph / KB over one workspace ---------------------------------------
def _rebased(
    records: list[EvidenceRecord], workspace: Workspace
) -> list[EvidenceRecord]:
    """Point origins at the workspace's real on-disk path (ids/locators stay)."""
    prefix = f"var/connect/{workspace.name}/"
    return [
        replace(
            record,
            origin=replace(
                record.origin,
                source=prefix + record.origin.source.removeprefix("github_actions/"),
            ),
        )
        for record in records
    ]


def workspace_records(workspace: Workspace) -> list[EvidenceRecord]:
    """Every record of the snapshot: runs + failed-step log chunks + PR rows."""
    source = GitHubActionsSource(data_dir=workspace.path)
    return _rebased(source.ingest(), workspace) + PRSource(workspace).ingest()


def build_workspace_kb(workspace: Workspace) -> KnowledgeBase:
    return KnowledgeBase(records=tuple(workspace_records(workspace)))


def build_workspace_graph(workspace: Workspace) -> KnowledgeGraph:
    """The snapshot as a graph — the ``build_github_actions_graph`` assembly
    (run rows with structured attributes, log chunks as ``document`` nodes,
    ``log_of`` edges), plus PR rows as plain structured nodes. No resolution
    layer: a CI snapshot carries no catalog to resolve against (ADR 0014)."""
    source = GitHubActionsSource(data_dir=workspace.path)
    node_attrs = source.node_attributes()

    graph = KnowledgeGraph()
    for record in workspace_records(workspace):
        if record.origin.locator.kind in _CHUNK_LOCATOR_KINDS:
            kind = "document"
        else:
            kind = record.id.split(":", 1)[0]  # "Run" / "PR"
        graph.add_node(
            Node(
                record=record,
                kind=kind,
                attributes=node_attrs.get(record.id, ()),
            )
        )
    for src, dst, relation in source.structural_edges():
        graph.add_edge(Edge(src=src, dst=dst, relation=relation))
    return graph


# --- the routed ask path ------------------------------------------------------------
def answer_workspace(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase
) -> tuple[Route, Answer]:
    """Route a BYO question the way the measured battery answers it.

    A named run id → the unchanged DevEx RCA (grounded claims over the run
    row + failed-step log spans, recurrence when a prior run shares the
    signature; refusals for passed/unknown runs). Anything else → the
    engine's lexical lookup, which refuses honestly on zero overlap.
    """
    match = RUN_ID.search(question)
    if match:
        route = Route(
            kind="rca",
            reason=f"names pipeline run {match.group(0)} — root-cause analysis",
        )
        return route, explain_failure(question, graph)
    route = Route(
        kind="lookup",
        reason="no run named — lexical lookup over the workspace snapshot",
    )
    return route, retrieve_answer(question, kb)
