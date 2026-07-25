"""``tessera proof`` — run the bounded soundness theorem (spec 0147).

Offline, deterministic, stdlib-only: exhaustive enumeration over a finite
domain is a decision procedure, so no SMT solver is needed and a reviewer
can audit the whole argument by reading four small files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tessera.bundle.canonical import canonical_bytes
from tessera.proof import universe as uni
from tessera.proof.check import render_certificate, run_proof

CERTIFICATE_PATH = Path("data/proof/certificate.json")

_DESCRIPTION = """\
Machine-check the soundness theorem: over a bounded universe of bundle
states enumerated IN FULL, a PASS from the re-executing verifier implies
the state is honest — no false PASS exists, not merely "none was found".

Two deliberately flawed verifiers are checked in the same run and MUST be
refuted with concrete counterexamples, so the checker is demonstrably able
to fail. The model's claim semantics are differentially checked against the
shipping verifier over the same domain.

The bound is part of the result and is printed with it. What this does not
prove is printed too.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera proof",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the machine-readable certificate"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="also enumerate the three-claim universe (~4.4M states, minutes)",
    )
    parser.add_argument(
        "--write",
        type=Path,
        default=None,
        help=f"write the certificate JSON (the committed copy lives at "
        f"{CERTIFICATE_PATH})",
    )
    args = parser.parse_args(argv)

    bounds: tuple[uni.Bounds, ...] = uni.DEFAULT_UNIVERSES
    if args.deep:
        bounds = (*bounds, uni.UNIVERSE_DEEP)

    certificate = run_proof(bounds)

    if args.write is not None:
        payload = canonical_bytes(certificate.to_dict()) + b"\n"
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_bytes(payload)
        print(f"wrote {args.write} ({len(payload):,} bytes)")
        return 0 if certificate.proved else 1

    if args.json:
        print(json.dumps(certificate.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_certificate(certificate))
    # A failed proof — or a negative control that was NOT refuted — is a
    # non-zero exit, so this can gate a build.
    return 0 if certificate.proved else 1
