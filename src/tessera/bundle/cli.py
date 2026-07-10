"""The ``tessera bundle`` command — emit a sealed trust bundle (spec 0133).

Dispatched from the front door (``tessera/cli.py``, the spec-0117 pattern).
``tessera verify`` — the offline re-executing check — arrives with unit
0134 and will live beside this entry.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tessera.agent.grounded import available_domains
from tessera.bundle.emit import build_bundle, write_bundle

_DESCRIPTION = """\
Emit a sealed trust bundle: one .tsb file carrying the grounded answer (or
the explicit refusal), the full evidence closure (graph + knowledge base),
the engine pins, and an integrity manifest sealed by a root hash — the
portable record `tessera verify` re-checks offline by re-execution.
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tessera bundle",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("question", help="the question to ground and package")
    parser.add_argument(
        "--domain",
        required=True,
        choices=available_domains(),
        help="the committed domain to ground in",
    )
    parser.add_argument(
        "-o",
        "--out",
        default="answer.tsb",
        help="output path (default: answer.tsb)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        bundle = build_bundle(args.domain, args.question)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    size = write_bundle(bundle, Path(args.out))

    result = bundle["result"]
    assert isinstance(result, dict)
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    claims = result["claims"]
    assert isinstance(claims, list)

    if result["refused"]:
        print(f"outcome: refusal — {result['refusal']}")
    else:
        verified = sum(
            1 for claim in claims if isinstance(claim, dict) and claim["verified"]
        )
        print(f"outcome: grounded — {verified}/{len(claims)} claim(s) verified")
    print(f"root:    {integrity['root']}")
    print(f"wrote:   {args.out} ({size:,} bytes)")
    return 0
