"""Command-line surface for the Phase 0 hello-world.

A thin wrapper over :func:`tessera.grounding.answer`. With no arguments it
answers the built-in demo question; pass a question to try your own (including
one with no supporting evidence, to see the principled refusal).

    uv run tessera                       # the built-in demo question
    uv run tessera "your question here"   # try your own
    uv run tessera "Who is Acme's CEO?"   # unsupported -> principled refusal
"""

from __future__ import annotations

import argparse

from tessera.grounding import answer
from tessera.knowledge import DEMO_KB, DEMO_QUESTION


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera",
        description=(
            "Ask a grounded question. Every claim in the answer is traced to "
            "the source records that support it; unsupported questions are "
            "declined rather than guessed."
        ),
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=DEMO_QUESTION,
        help="The question to answer (defaults to the built-in demo question).",
    )
    args = parser.parse_args(argv)

    print(answer(args.question, DEMO_KB).render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
