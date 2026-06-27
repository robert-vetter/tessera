"""Command-line surface for the eval harness: ``uv run tessera-eval``.

Prints the current gold + synthetic trust numbers and exits non-zero when the
faithfulness floor is broken (ADR 0005/0007) — this is what ``/verify`` step 5
runs. ``--record`` additionally appends the run to ``eval/history.jsonl`` and
regenerates the faithfulness badge; recording is a deliberate checkpoint, so
pair it with ``--note`` explaining what changed.
"""

from __future__ import annotations

import argparse

from tessera.eval.harness import run_eval
from tessera.eval.history import record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tessera-eval")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Append this run to eval/history.jsonl and refresh eval/badge.json.",
    )
    parser.add_argument(
        "--note",
        default="",
        help="Why this run is being recorded (stored in the history entry).",
    )
    parser.add_argument(
        "--recorded",
        default=None,
        help=(
            "Override the recorded date (ISO 'YYYY-MM-DD') for the history entry; "
            "defaults to today. Use to stamp a one-shot online measurement."
        ),
    )
    args = parser.parse_args(argv)

    report = run_eval()
    print(report.summary())

    if args.record:
        record(report, note=args.note, recorded=args.recorded)
        print("Recorded to eval/history.jsonl; badge refreshed.")

    # Faithfulness is the one hard floor, on BOTH batteries: an unsupported
    # claim fails the build (ADR 0005, ADR 0007). Coverage and quality are
    # reported as honest, improvable targets.
    if not report.floor_holds:
        print("FAIL: faithfulness < 1.000 — a claim is unsupported by its evidence.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
