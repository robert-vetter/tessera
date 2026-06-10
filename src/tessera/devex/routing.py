"""DevEx question routing: which answer path, and why — explainably.

The vertical's own dispatch (spec 0031): question shapes are per-vertical
(ADR 0008), so this module decides between root-cause analysis (a pipeline
run is named), a change summary (a PR is named), a service-ownership lookup
(a catalog service is named — by name, resolved variant, or declared alias;
spec 0036), and the engine's unchanged lexical lookup over the DevEx
knowledge base (everything else — which refuses honestly on zero overlap).
The `Route` value and the discipline — every decision carries a
human-readable reason; fallthrough refuses rather than guesses — are the
core router's, reused unchanged.
"""

from __future__ import annotations

from tessera.devex.ownership import find_service, service_lookup
from tessera.devex.rca import RUN_ID, explain_failure
from tessera.devex.summaries import PR_ID, summarize_change
from tessera.graph import KnowledgeGraph
from tessera.grounding import Answer, KnowledgeBase
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route


def classify(question: str, graph: KnowledgeGraph | None = None) -> Route:
    """Classify a DevEx question by what answering it would take.

    A named run wins over a named PR when both appear (the failure is the
    more specific subject — a recorded rule, spec 0031). Service detection
    needs the graph's names/aliases, so it only participates when a graph is
    supplied (``route`` always supplies one).
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
    if graph is not None:
        match = find_service(question, graph)
        if match.status != "none":
            return Route(
                kind="service",
                reason="names a catalog service — ownership/catalog lookup",
            )
    return Route(kind="lookup", reason="no run, PR, or service named — lexical lookup")


def route(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase
) -> tuple[Route, Answer]:
    """Classify, dispatch, and return both the route and the answer."""
    decision = classify(question, graph)
    if decision.kind == "rca":
        return decision, explain_failure(question, graph)
    if decision.kind == "summary":
        return decision, summarize_change(question, graph)
    if decision.kind == "service":
        return decision, service_lookup(question, graph)
    return decision, retrieve_answer(question, kb)
