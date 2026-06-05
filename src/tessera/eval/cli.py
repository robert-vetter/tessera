"""Command-line surface for the eval harness: ``uv run tessera-eval``.

Prints the current eval report. Today that is an honest "no gold set evaluated
yet"; once Unit 6 adds the gold set and metrics, the same command reports the
faithfulness, coverage, and quality numbers. This is the command ``/verify``
step 5 runs.
"""

from __future__ import annotations

from tessera.eval.harness import run_eval


def main(argv: list[str] | None = None) -> int:
    print(run_eval().summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
