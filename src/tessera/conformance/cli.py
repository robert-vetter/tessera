"""``tessera conformance`` — run the Verification Gap benchmark (spec 0146).

Offline, deterministic, stdlib-only. ``--json`` emits the machine-readable
scorecard (the shape committed at ``data/conformance/scorecard.json`` and
pinned by a test, so a published number can never drift from the code that
produced it).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tessera.bundle.canonical import canonical_bytes
from tessera.conformance.runner import render_scorecard, run_benchmark

SCORECARD_PATH = Path("data/conformance/scorecard.json")

_DESCRIPTION = """\
Grade the published agent-receipt verification methods of 2026 against an
attack battery, under two named threat models.

The methods are OUR implementations of PUBLISHED methods (hash-chained
receipts; IETF-style signed receipts; policy/covenant-bound receipts;
runtime-attestation validator invariants), written to be as strong as
their sources describe. No third-party product is run, named in a score,
or characterised beyond its own published description.

Read the outside-tamperer table first: there, signatures detect
everything and re-execution adds nothing. The gap belongs to the second
model — where the party sealing the receipt is the party whose honesty is
in question.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera conformance",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the machine-readable scorecard"
    )
    parser.add_argument(
        "--write",
        type=Path,
        default=None,
        help=f"write the scorecard JSON to a path (the committed copy lives at "
        f"{SCORECARD_PATH})",
    )
    args = parser.parse_args(argv)

    card = run_benchmark()
    payload = canonical_bytes(card.to_dict()) + b"\n"

    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_bytes(payload)
        print(f"wrote {args.write} ({len(payload):,} bytes)")
        return 0

    if args.json:
        print(json.dumps(card.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_scorecard(card))
    return 0
