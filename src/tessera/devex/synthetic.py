"""Synthetic DevEx eval cases, enumerated from the graph (ADR 0007 applied).

Deterministic — no RNG, no LLM, nothing committed: cases derive from the
DevEx graph's content at eval time, and **expectations come from the data**,
never from running the engine (the anti-tautology rule): an RCA case's
expected support is the run row plus the log chunks that *textually* carry
an ERROR line; its expected facts come from the run's own attributes; a
summary case's expected ticket is parsed from the PR row's text. The
recurrence/incident claims are deliberately *not* echoed as expectations —
their correctness is stressed where it belongs, by the faithfulness
verifier recomputing every emitted claim.
"""

from __future__ import annotations

import re

from tessera.eval.battery import GoldCase
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase
from tessera.retrieval import _tokenize

_TICKET_REF = re.compile(r"\bDEVEX-\d+\b")

# Questions whose content tokens must be absent from the corpus — verified
# against the actual vocabulary before emitting (data-derived, ADR 0007).
_MISSING_EVIDENCE_TEMPLATES = (
    "What colour is the sky?",
    "Do we operate a zeppelin fleet?",
    "Which volcano permits were filed?",
)


def _of_kind(graph: KnowledgeGraph, kind: str) -> list[Node]:
    return sorted((n for n in graph.nodes if n.kind == kind), key=lambda n: n.id)


def generate_cases(graph: KnowledgeGraph, kb: KnowledgeBase) -> list[GoldCase]:
    """Enumerate the deterministic DevEx battery for the current graph."""
    cases: list[GoldCase] = []
    node_ids = {n.id for n in graph.nodes}

    # --- one RCA case per failed run; one refused premise per passed run ------
    for run in _of_kind(graph, "Run"):
        run_ref = run.id.removeprefix("Run:")
        question = f"Why did run {run_ref} fail?"
        if run.attr("status") == "failed":
            error_chunks = sorted(
                chunk_id
                for chunk_id in graph.sources_of({run.id}, "log_of")
                if "ERROR" in graph.node(chunk_id).record.text
            )
            cases.append(
                GoldCase(
                    id=f"syn_devex_rca_{run_ref}",
                    question=question,
                    engine="route",
                    kind="answer",
                    expected_support=(run.id, *error_chunks),
                    expected_facts=(
                        f"status failed (failing job {run.attr('failed_job')})",
                    ),
                )
            )
        else:
            cases.append(
                GoldCase(
                    id=f"syn_devex_refuse_passed_{run_ref}",
                    question=question,
                    engine="route",
                    kind="refuse",
                )
            )

    # --- one summary case per PR ------------------------------------------------
    for pr in _of_kind(graph, "PR"):
        pr_ref = pr.id.removeprefix("PR:")
        hunks = sorted(graph.sources_of({pr.id}, "diff_of"))
        ticket_refs = [
            f"Ticket:{ref}"
            for ref in dict.fromkeys(_TICKET_REF.findall(pr.record.text))
            if f"Ticket:{ref}" in node_ids
        ]
        cases.append(
            GoldCase(
                id=f"syn_devex_summary_{pr_ref}",
                question=f"What does {pr_ref} change?",
                engine="route",
                kind="answer",
                expected_support=(pr.id, *hunks, *ticket_refs),
                expected_facts=tuple(
                    ref.removeprefix("Ticket:") for ref in ticket_refs
                ),
            )
        )

    # --- refusals -----------------------------------------------------------------
    for unknown, label in (("R-99999", "run"), ("PR-99999", "pr")):
        prefix = "Run:" if label == "run" else "PR:"
        assert f"{prefix}{unknown}" not in node_ids
        question = (
            f"Why did run {unknown} fail?"
            if label == "run"
            else f"What does {unknown} change?"
        )
        cases.append(
            GoldCase(
                id=f"syn_devex_refuse_unknown_{label}",
                question=question,
                engine="route",
                kind="refuse",
            )
        )

    vocabulary = {token for record in kb.records for token in _tokenize(record.text)}
    for index, template in enumerate(_MISSING_EVIDENCE_TEMPLATES, start=1):
        if any(token in vocabulary for token in _tokenize(template)):
            continue  # a content token exists in the corpus: not a missing case
        cases.append(
            GoldCase(
                id=f"syn_devex_refuse_missing_{index}",
                question=template,
                engine="route",
                kind="refuse",
            )
        )

    cases.sort(key=lambda c: c.id)
    return cases
