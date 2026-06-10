"""DevEx question routing: which answer path, and why — explainably.

The vertical's own dispatch (spec 0031): question shapes are per-vertical
(ADR 0008), so this module decides between root-cause analysis (a pipeline
run is named), a change summary (a PR is named), and the engine's unchanged
lexical lookup over the DevEx knowledge base (everything else — which
refuses honestly on zero overlap). The `Route` value and the discipline —
every decision carries a human-readable reason; fallthrough refuses rather
than guesses — are the core router's, reused unchanged.
"""

from __future__ import annotations

from tessera.devex.rca import RUN_ID, explain_failure
from tessera.devex.summaries import PR_ID, summarize_change
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, KnowledgeBase
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route


def classify(question: str) -> Route:
    """Classify a DevEx question by what answering it would take.

    A named run wins over a named PR when both appear (the failure is the
    more specific subject — a recorded rule, spec 0031).
    """
    run = RUN_ID.search(question)
    if run:
        return Route(
            kind="rca",
            reason=f"names pipeline run {run.group(0)} — root-cause analysis",
        )
    pr = PR_ID.search(question)
    if pr:
        return Route(
            kind="summary",
            reason=f"names pull request {pr.group(0)} — change summary",
        )
    return Route(kind="lookup", reason="no run or PR named — lexical lookup")


def route(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase
) -> tuple[Route, Answer]:
    """Classify, dispatch, and return both the route and the answer."""
    decision = classify(question)
    if decision.kind == "rca":
        return decision, explain_failure(question, graph)
    if decision.kind == "summary":
        return decision, summarize_change(question, graph)
    return decision, retrieve_answer(question, kb)
