"""``tessera ledger`` — inspect the issuance log and produce proofs (spec 0151).

Offline and stdlib-only. The log itself is a text file of sealed roots in
issuance order; everything interesting is a proof *about* it:

  head          what you publish, and what a verifier must obtain out of band
  prove         an inclusion proof for one receipt, against the current head
  consistency   proof that the current head extends an earlier one
  check         verify a proof you were handed, against a head YOU hold
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tessera.bundle.canonical import canonical_bytes
from tessera.ledger.store import (
    Head,
    Ledger,
    LedgerError,
    check_consistency,
    check_inclusion,
    load_proof,
)

DEFAULT_LEDGER = Path("var/ledger/issued.log")

_DESCRIPTION = """\
The append-only issuance log. Ten layers answer "is this receipt honest?";
this answers "is this all of them?" — a receipt an operator never recorded
has no inclusion proof, and a rewritten history cannot produce a
consistency proof.

Bounded, and the bound is part of the claim: an operator who keeps two
logs can show two heads, and no offline check detects that. Consistency
proofs make rewriting detectable to anyone who has seen an EARLIER head;
making heads unforgeably public is what a public transparency log is for.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera ledger",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ledger", type=Path, default=DEFAULT_LEDGER, help="the log file"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("head", help="print the current size and Merkle head")

    prove = sub.add_parser("prove", help="inclusion proof for a receipt root")
    prove.add_argument("root", help="the bundle's sealed root")
    prove.add_argument("-o", "--out", type=Path, default=None)

    consistency = sub.add_parser(
        "consistency", help="prove the current head extends an earlier size"
    )
    consistency.add_argument("old_size", type=int)
    consistency.add_argument("-o", "--out", type=Path, default=None)

    check = sub.add_parser("check", help="verify a proof you were handed")
    check.add_argument("proof", type=Path)
    check.add_argument(
        "--head", default=None, help="the head you already hold, '<size>:sha256:…'"
    )
    check.add_argument("--root", default=None, help="the receipt root it must prove")

    args = parser.parse_args(argv)
    log = Ledger(args.ledger)

    try:
        if args.command == "head":
            head = log.head()
            print(head)
            print(f"entries: {head.size}")
            return 0

        if args.command == "prove":
            proof = log.prove(args.root)
            data = canonical_bytes(proof) + b"\n"
            if args.out:
                args.out.write_bytes(data)
                print(f"wrote {args.out} (head {log.head()})")
            else:
                print(json.dumps(proof, indent=2))
            return 0

        if args.command == "consistency":
            proof = log.consistency(args.old_size)
            data = canonical_bytes(proof) + b"\n"
            if args.out:
                args.out.write_bytes(data)
                print(f"wrote {args.out}")
            else:
                print(json.dumps(proof, indent=2))
            return 0

        artifact = load_proof(args.proof)
        if "from" in artifact and "to" in artifact:
            problem = check_consistency(artifact)
            print(
                "consistency: the later head extends the earlier one — nothing "
                "was rewritten"
                if problem is None
                else f"consistency: REFUSED — {problem}"
            )
            return 0 if problem is None else 2

        if args.head is None or args.root is None:
            print(
                "inclusion: not checked — an inclusion proof means nothing "
                "without --head (a head you already hold) and --root",
            )
            return 2
        problem = check_inclusion(artifact, args.root, Head.parse(args.head))
        print(
            "inclusion: the receipt is in the log at the head you supplied"
            if problem is None
            else f"inclusion: REFUSED — {problem}"
        )
        return 0 if problem is None else 2
    except LedgerError as error:
        print(f"error: {error}")
        return 2
