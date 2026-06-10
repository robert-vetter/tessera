"""The DevEx vertical's routed door: ``uv run tessera-devex "<question>"``.

The second vertical's counterpart to ``uv run tessera`` (spec 0031): the
router decides between root-cause analysis, a change summary, a
service-ownership lookup (spec 0036), and lexical lookup — and says so,
because *why a question went where* is part of an explainable answer.
``--engine`` forces a path.

    uv run tessera-devex                                  # flagship RCA demo
    uv run tessera-devex "What does PR-201 change?"
    uv run tessera-devex "Who is on call for payments-service?"
    uv run tessera-devex "What colour is the sky?"        # honest refusal
"""

from __future__ import annotations

import argparse

from tessera.devex.knowledge import DEMO_QUESTION, build_devex_graph, build_devex_kb
from tessera.devex.routing import route
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-devex",
        description=(
            "Ask a grounded DevEx question (pipeline failures, PR changes, "
            "tickets). The router picks the answer path and explains its "
            "pick; every claim is traced to log lines, diff hunks, or rows; "
            "unanswerable questions are declined rather than guessed."
        ),
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEMO_QUESTION,
        help="The question to answer (defaults to the built-in demo question).",
    )
    parser.add_argument(
        "--engine",
        choices=("auto", "retrieve", "rca", "summary", "service"),
        default="auto",
        help="Force a specific answer path instead of auto-routing.",
    )
    args = parser.parse_args(argv)

    if args.engine == "retrieve":
        # Pure lookup needs no graph build.
        print(retrieve_answer(args.question, build_devex_kb()).render())
        return 0

    graph = build_devex_graph()
    if args.engine == "rca":
        from tessera.devex.rca import explain_failure

        print(explain_failure(args.question, graph).render())
        return 0
    if args.engine == "summary":
        from tessera.devex.summaries import summarize_change

        print(summarize_change(args.question, graph).render())
        return 0
    if args.engine == "service":
        from tessera.devex.ownership import service_lookup

        print(service_lookup(args.question, graph).render())
        return 0

    decision: Route
    decision, answer = route(args.question, graph, build_devex_kb())
    print(f"[route: {decision.kind} — {decision.reason}]")
    print(answer.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
