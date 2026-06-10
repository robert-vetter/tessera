"""The one routed door: ``uv run tessera "<question>"``.

The router (spec 0020) decides whether a question is a simple lookup, a
one-entity cross-source composition, or multi-step reasoning — and says so:
the route and its reason are printed above the answer, because *why a question
went where* is part of an explainable system. ``--engine`` forces a path.

    uv run tessera                                      # demo question, auto-routed
    uv run tessera "Compare Müller Logistik and Nordwind Logistik totals."
    uv run tessera "Which entity has the highest total order value in EUR?"
    uv run tessera "What colour is the sky?"            # honest refusal
"""

from __future__ import annotations

import argparse

from tessera.knowledge import DEMO_KB, DEMO_QUESTION, build_demo_graph
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route, route


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera",
        description=(
            "Ask a grounded question. The router picks the answer path (and "
            "explains its pick); every claim is traced to source records; "
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
        choices=("auto", "retrieve", "compose", "reason"),
        default="auto",
        help="Force a specific answer path instead of auto-routing.",
    )
    args = parser.parse_args(argv)

    if args.engine == "retrieve":
        # Pure lookup needs no graph build.
        print(retrieve_answer(args.question, DEMO_KB).render())
        return 0

    graph = build_demo_graph()
    if args.engine == "compose":
        from tessera.composition import compose

        print(compose(args.question, graph).render())
        return 0
    if args.engine == "reason":
        from tessera.reasoning import reason

        print(reason(args.question, graph).render())
        return 0

    decision: Route
    decision, answer = route(args.question, graph, DEMO_KB)
    print(f"[route: {decision.kind} — {decision.reason}]")
    print(answer.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
