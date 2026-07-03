"""The per-repo smoke battery — the trust floor for a connected repository.

A connected workspace has no gold set (its data is foreign and uncommitted),
so the honest floor is a check *derived from the snapshot itself*: does the
trust contract actually hold on this repo's data? (spec 0119). Five hard
checks plus one named caveat, each computed from the workspace — no authored
expectations:

- **runs-parse** — the snapshot ingests and yields at least one run row.
- **failed-run-grounds** — the most recent failed run with a log produces a
  grounded RCA (skipped, honestly, when the snapshot is metadata-only).
- **claims-supported** — every claim of that RCA passes the eval's OWN
  ``is_supported`` verifier — the exact check the measured batteries run.
- **provenance-resolves** — every cited origin resolves to a file that exists
  in the workspace (Pillar 1, end to end).
- **refusals-fire** — a passed run refuses as passed; an unknown run id
  refuses by name.
- **recurrence-signal** (warn, not fail) — if the RCA's recurrence claim keys
  on a bare ``Process completed with exit code N.`` trailer, the report warns:
  the claim is true and verifier-passed, but the recurrence label is weak (the
  spec 0118 named limitation surfaced here).

Reported, never CI-gated: foreign data is not committed, so this runs on
demand (``tessera smoke``), not in ``scripts/gate.sh``. Its own logic is
CI-covered by tests over a synthetic committed fixture workspace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from tessera.connect.workspace import (
    Workspace,
    answer_workspace,
    build_workspace_graph,
    build_workspace_kb,
)
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer

# A recurrence signature that is only a generic exit-code trailer — the weak
# signal named in spec 0118 (matches the RCA claim text's quoted fragment).
# `-?`: negative exit codes are real on Windows runners; this regex and
# rca.py's `_GENERIC_TRAILER` encode ONE definition of "generic trailer" and
# must move together (spec 0126 scope amendment), or a negative-code trailer
# would count as "sharp" in rca yet escape this WARN.
_TRAILER = re.compile(r'"Process completed with exit code -?\d+\.?"')
# An id that cannot exist in any snapshot (11 nines) — for the unknown refusal.
_UNKNOWN_RUN_ID = "99999999999"


class Outcome(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


@dataclass(frozen=True)
class Check:
    name: str
    outcome: Outcome
    detail: str


@dataclass(frozen=True)
class SmokeReport:
    repo: str
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        """True iff no hard check failed (skips and warns do not fail the run)."""
        return all(check.outcome != Outcome.FAIL for check in self.checks)

    def render(self) -> str:
        symbol = {
            Outcome.PASS: "PASS",
            Outcome.FAIL: "FAIL",
            Outcome.SKIP: "SKIP",
            Outcome.WARN: "WARN",
        }
        lines = [f"smoke battery for github.com/{self.repo}:"]
        for check in self.checks:
            lines.append(f"  [{symbol[check.outcome]}] {check.name} — {check.detail}")
        verdict = "all hard checks passed" if self.ok else "one or more checks FAILED"
        lines.append(f"  → {verdict}.")
        return "\n".join(lines)


def _failed_runs_with_logs(graph: KnowledgeGraph) -> list[str]:
    """Failed run ids that have at least one log chunk, newest id first."""
    out: list[str] = []
    for node in graph.nodes:
        if node.kind != "Run" or node.attr("status") != "failed":
            continue
        if graph.sources_of({node.id}, "log_of"):
            out.append(node.record.id.removeprefix("Run:"))
    return sorted(out, key=lambda i: (len(i), i), reverse=True)


def _passed_runs(graph: KnowledgeGraph) -> list[str]:
    return sorted(
        node.record.id.removeprefix("Run:")
        for node in graph.nodes
        if node.kind == "Run" and node.attr("status") == "passed"
    )


def run_smoke(workspace: Workspace) -> SmokeReport:
    """Derive and run the five checks (plus the recurrence caveat) over one
    connected workspace. Pure over the snapshot — no network."""
    graph = build_workspace_graph(workspace)
    kb = build_workspace_kb(workspace)
    checks: list[Check] = []

    # 1) runs-parse
    run_nodes = [n for n in graph.nodes if n.kind == "Run"]
    if run_nodes:
        checks.append(
            Check("runs-parse", Outcome.PASS, f"{len(run_nodes)} run row(s) ingested")
        )
    else:
        checks.append(Check("runs-parse", Outcome.FAIL, "no run rows in the snapshot"))
        return SmokeReport(repo=workspace.repo, checks=tuple(checks))

    # 2–4 + recurrence caveat: the RCA over the newest failed run with a log.
    failed = _failed_runs_with_logs(graph)
    if not failed:
        checks.append(
            Check(
                "failed-run-grounds",
                Outcome.SKIP,
                "no failed run with a log (metadata-only snapshot?) — RCA "
                "not exercised",
            )
        )
    else:
        run_id = failed[0]
        _, answer = answer_workspace(f"Why did run {run_id} fail?", graph, kb)
        checks.extend(_rca_checks(run_id, answer, graph, workspace))

    # 5) refusals-fire — a passed run and an unknown run must both refuse.
    checks.append(_refusal_check(graph, kb))

    return SmokeReport(repo=workspace.repo, checks=tuple(checks))


def _rca_checks(
    run_id: str, answer: Answer, graph: KnowledgeGraph, workspace: Workspace
) -> list[Check]:
    checks: list[Check] = []
    if not answer.is_grounded or not answer.claims:
        checks.append(
            Check(
                "failed-run-grounds",
                Outcome.FAIL,
                f"run {run_id} produced no grounded claims",
            )
        )
        return checks
    checks.append(
        Check(
            "failed-run-grounds",
            Outcome.PASS,
            f"run {run_id} → {len(answer.claims)} grounded claim(s)",
        )
    )

    # claims-supported — the eval's own verifier, unchanged.
    nodes = {node.id: node for node in graph.nodes}
    unsupported = [
        claim for claim in answer.claims if not is_supported(claim, nodes, graph)
    ]
    if unsupported:
        checks.append(
            Check(
                "claims-supported",
                Outcome.FAIL,
                f"{len(unsupported)} of {len(answer.claims)} claim(s) "
                "fail is_supported",
            )
        )
    else:
        checks.append(
            Check(
                "claims-supported",
                Outcome.PASS,
                f"all {len(answer.claims)} claim(s) pass is_supported",
            )
        )

    # provenance-resolves — every cited origin exists on disk.
    missing = _unresolvable_origins(answer, workspace)
    if missing:
        checks.append(
            Check(
                "provenance-resolves",
                Outcome.FAIL,
                f"{len(missing)} cited origin(s) do not resolve: {missing[0]}",
            )
        )
    else:
        checks.append(
            Check(
                "provenance-resolves",
                Outcome.PASS,
                "every cited origin resolves to a workspace file",
            )
        )

    # recurrence-signal — warn on a bare exit-code trailer (spec 0118 caveat).
    trailer_claims = [c for c in answer.claims if _is_trailer_recurrence(c.text)]
    if trailer_claims:
        checks.append(
            Check(
                "recurrence-signal",
                Outcome.WARN,
                "a recurrence claim keys on a generic 'exit code N' trailer — "
                "true and verifier-passed, but a weak recurrence signal "
                "(spec 0118 limitation)",
            )
        )
    return checks


def _unresolvable_origins(answer: Answer, workspace: Workspace) -> list[str]:
    """Cited origins whose file is not present in the workspace directory.

    The displayed origin is the rebased ``var/connect/<name>/…`` path; here we
    resolve it against the workspace's ACTUAL location (which is where
    ``var/connect/<name>`` points when ``ask`` is run from the invocation
    directory) so the check is correct regardless of cwd.
    """
    prefix = f"var/connect/{workspace.name}/"
    missing: list[str] = []
    for claim in answer.claims:
        for record in claim.support:
            source = record.origin.source
            if not source.startswith(prefix):
                missing.append(source)
                continue
            relative = source.removeprefix(prefix)
            if not (workspace.path / relative).is_file():
                missing.append(source)
    return missing


def _refusal_check(graph: KnowledgeGraph, kb: object) -> Check:
    from tessera.grounding import KnowledgeBase

    assert isinstance(kb, KnowledgeBase)
    # An unknown run id must refuse by name.
    _, unknown = answer_workspace(f"Why did run {_UNKNOWN_RUN_ID} fail?", graph, kb)
    if unknown.is_grounded:
        return Check(
            "refusals-fire", Outcome.FAIL, "an unknown run id was answered, not refused"
        )
    # A passed run (if any) must refuse as passed.
    passed = _passed_runs(graph)
    if passed:
        _, answer = answer_workspace(f"Why did run {passed[0]} fail?", graph, kb)
        if answer.is_grounded:
            return Check(
                "refusals-fire",
                Outcome.FAIL,
                f"passed run {passed[0]} was answered, not refused",
            )
        return Check(
            "refusals-fire",
            Outcome.PASS,
            f"unknown id and passed run {passed[0]} both refuse",
        )
    return Check(
        "refusals-fire",
        Outcome.PASS,
        "unknown id refuses (no passed run in the snapshot to test)",
    )


def _is_trailer_recurrence(text: str) -> bool:
    return text.startswith("Recurring failure:") and bool(_TRAILER.search(text))
