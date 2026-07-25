"""The ``tessera`` front door: BYO + bundle subcommands, else the business demo.

A thin dispatcher (spec 0117 decision 5): when the first argument is exactly
one of the reserved subcommands — ``connect``, ``ask``, ``smoke``, ``ingest``
(the BYO paths, Milestone 18) or ``bundle``/``verify`` (trust bundles,
Milestone 20) — the invocation goes to that path;
anything else falls through to the business CLI with identical behaviour, so
``uv run tessera "Which customers …?"`` keeps working exactly as every README
example shows.

Recorded residual (spec 0117, extended by spec 0133): a business *question*
whose first word is literally a reserved word would mis-route — rephrase it
or use ``tessera-chat``. The reserved words are not natural question openers.
"""

from __future__ import annotations

import sys

# Reserved from the start so the dispatch contract is stable across the
# milestone: `smoke` and `ingest` are claimed now and arrive with their units.
_BYO_COMMANDS = frozenset({"connect", "ask", "smoke", "ingest"})

_TOP_HELP = """\
tessera — grounded answers with claim-level provenance.

Bring-your-own-data (Milestone 18):
  tessera connect github <owner>/<repo>   fetch a bounded, scrubbed snapshot
  tessera ingest <dir>                    ingest a CSV + Markdown directory
  tessera ask <owner>/<repo>|<dir> "<q>"  answer over a repo or a directory
  tessera smoke <owner>/<repo>            check the trust contract holds on it

Trust bundles (Milestones 20–22):
  tessera bundle "<q>" --domain <d>       emit a sealed, portable trust bundle
  tessera verify <file>.tsb               re-execute its verification, offline
  tessera bundle explain <file>.tsb       render its chain legibly for a human
  tessera bundle audit <file>.tsb         decision record (EU AI Act mapping)
  tessera bundle chain "<q>" <a.tsb> ...  chain bundles: verified answers
                                          become evidence; verify re-executes
                                          the whole chain from one file
  tessera bundle approve <file>.tsb       sign a detached approval bound to
                                          the exact sealed bytes; check with
                                          verify --approval (+ policy rules)
  tessera bundle redact <file>.tsb        withhold evidence, keep the root —
                                          share the receipt, not the data
  tessera bundle attest <file>.tsb        record it in the issuance log
  tessera ledger head|prove|check         "is this all of them?" — inclusion
                                          and consistency proofs, offline

The Verification Gap benchmark (Milestone 22):
  tessera conformance                     grade the published verification
                                          methods against an attack battery,
                                          under two named threat models
  tessera proof                           machine-check the bounded soundness
                                          theorem: over every state of a
                                          bounded universe, no false PASS

Otherwise the argument is a business-vertical question:
  tessera "Which customer has the highest total order value?"

See also: tessera-devex, tessera-chat, tessera-ui, tessera-eval.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    # A leading --help at the front door lists the BYO subcommands too (a
    # business question is never literally "-h"/"--help").
    if args and args[0] in ("-h", "--help"):
        print(_TOP_HELP)
        return 0
    if args and args[0] == "bundle":
        from tessera.bundle.cli import main as bundle_main

        return bundle_main(args[1:])
    if args and args[0] == "verify":
        from tessera.bundle.cli import verify_main

        return verify_main(args[1:])
    if args and args[0] == "conformance":
        from tessera.conformance.cli import main as conformance_main

        return conformance_main(args[1:])
    if args and args[0] == "ledger":
        from tessera.ledger.cli import main as ledger_main

        return ledger_main(args[1:])
    if args and args[0] == "proof":
        from tessera.proof.cli import main as proof_main

        return proof_main(args[1:])
    if args and args[0] in _BYO_COMMANDS:
        from tessera.connect.cli import main as connect_main

        return connect_main(args)
    from tessera.business.cli import main as business_main

    return business_main(argv)
