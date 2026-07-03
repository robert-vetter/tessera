"""The ``tessera`` front door: BYO subcommands, else the business demo.

A thin dispatcher (spec 0117 decision 5): when the first argument is exactly
one of the reserved subcommands — ``connect``, ``ask``, ``smoke``, ``ingest``
— the invocation goes to the BYO paths (Milestone 18); anything else falls
through to the business CLI with identical behaviour, so ``uv run tessera
"Which customers …?"`` keeps working exactly as every README example shows.

Recorded residual (spec 0117): a business *question* whose first word is
literally a reserved word would mis-route — rephrase it or use
``tessera-chat``. The reserved words are not natural question openers.
"""

from __future__ import annotations

import sys

# Reserved from the start so the dispatch contract is stable across the
# milestone: `smoke` and `ingest` are claimed now and arrive with their units.
_BYO_COMMANDS = frozenset({"connect", "ask", "smoke", "ingest"})


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in _BYO_COMMANDS:
        if args[0] in ("connect", "ask"):
            from tessera.connect.cli import main as connect_main

            return connect_main(args)
        print(
            f"tessera {args[0]}: not available yet — this subcommand arrives "
            "with a later Milestone 18 unit (docs/ROADMAP2.md).",
            file=sys.stderr,
        )
        return 2
    from tessera.business.cli import main as business_main

    return business_main(argv)
