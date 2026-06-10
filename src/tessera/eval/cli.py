"""Command-line surface for the eval harness: ``uv run tessera-eval``.

Prints the current eval report. Today that is an honest "no gold set evaluated
yet"; once Unit 6 adds the gold set and metrics, the same command reports the
faithfulness, coverage, and quality numbers. This is the command ``/verify``
step 5 runs.
"""

from __future__ import annotations

from tessera.eval.harness import run_eval


def main(argv: list[str] | None = None) -> int:
    report = run_eval()
    print(report.summary())
    # Faithfulness is the one hard floor, on BOTH batteries: an unsupported
    # claim fails the build (ADR 0005, ADR 0007). Coverage and quality are
    # reported as honest, improvable targets.
    if not report.floor_holds:
        print("FAIL: faithfulness < 1.000 — a claim is unsupported by its evidence.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
