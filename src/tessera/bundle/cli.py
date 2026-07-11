"""The ``tessera bundle`` and ``tessera verify`` commands (specs 0133/0134).

Dispatched from the front door (``tessera/cli.py``, the spec-0117 pattern):
``bundle`` emits a sealed trust bundle; ``verify`` re-checks one offline by
re-execution — integrity and semantics, reported separately, exit codes
4 (envelope broken) > 2 (semantic failure) > 3 (degraded) > 0 (pass).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tessera.agent.grounded import available_domains
from tessera.bundle.emit import build_action_bundle, build_bundle, write_bundle
from tessera.bundle.verify import BundleFormatError, render_report, verify_bundle

_DESCRIPTION = """\
Emit a sealed trust bundle: one .tsb file carrying the grounded answer (or
the explicit refusal), the full evidence closure (graph + knowledge base),
the engine pins, and an integrity manifest sealed by a root hash — the
portable record `tessera verify` re-checks offline by re-execution.

With --action, the bundle also packages a simulated, grounded action (a
GitHub issue or PR comment): `tessera verify` then re-derives that the
wire request reconstructs from its slots and every value traces to a
verifier-passing claim.
"""

_ACTIONS = ("incident", "pr_summary")


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
    parser.add_argument(
        "--sign",
        action="store_true",
        help="sign the bundle's root with the Ed25519 key (needs the 'sign' extra)",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default=None,
        help="signing key path (default: var/keys/bundle_signing.key)",
    )
    parser.add_argument(
        "--action",
        choices=_ACTIONS,
        default=None,
        help="also package a simulated grounded action drafted from the answer",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # `tessera bundle keygen …` is a sibling verb, not a question. The front
    # door always passes an explicit argv list (spec 0117 dispatch).
    if argv and argv[0] == "keygen":
        return keygen_main(argv[1:])
    args = _parser().parse_args(argv)
    try:
        if args.action:
            bundle = build_action_bundle(args.action, args.domain, args.question)
        else:
            bundle = build_bundle(args.domain, args.question)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.sign:
        from tessera.bundle.signing import (
            DEFAULT_KEY_PATH,
            SigningUnavailableError,
            sign_bundle,
        )

        try:
            bundle = sign_bundle(bundle, args.key or DEFAULT_KEY_PATH)
        except (SigningUnavailableError, FileNotFoundError, ValueError) as error:
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
    action = bundle.get("action")
    if isinstance(action, dict):
        slots = action.get("slots")
        n = len(slots) if isinstance(slots, list) else 0
        request = action.get("request")
        method = request["method"] if isinstance(request, dict) else "?"
        print(f"action:  {action['kind']} — {method} ({n} grounded slot(s))")
    print(f"root:    {integrity['root']}")
    signature = bundle.get("signature")
    if isinstance(signature, dict):
        print(f"signed:  key {signature['public_key']}")
    print(f"wrote:   {args.out} ({size:,} bytes)")
    return 0


# --- tessera bundle keygen --------------------------------------------------------


def keygen_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera bundle keygen",
        description="Generate an Ed25519 signing keypair (needs the 'sign' extra).",
    )
    parser.add_argument(
        "--key",
        type=Path,
        default=None,
        help="key path (default: var/keys/bundle_signing.key; .pub alongside)",
    )
    args = parser.parse_args(argv)

    from tessera.bundle.signing import (
        DEFAULT_KEY_PATH,
        SigningUnavailableError,
        generate_keypair,
    )

    path = args.key or DEFAULT_KEY_PATH
    try:
        public_hex = generate_keypair(path)
    except (SigningUnavailableError, FileExistsError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote:      {path} (0600) and {path}.pub")
    print(f"public key: {public_hex}")
    return 0


# --- tessera verify ---------------------------------------------------------------

_VERIFY_DESCRIPTION = """\
Re-check a trust bundle offline by RE-EXECUTION: every recorded claim
verdict is re-derived from the evidence packaged in the file (the eval's
own deterministic verifier, re-run), and the packaged corpus must re-yield
the recorded answer for the recorded question. Integrity (hashes) and
semantics (truth of the record) are reported separately — a re-sealed
tampered file passes the first and fails the second.

Exit codes: 0 pass · 2 semantic failure · 3 degraded (visibly not
re-derivable) · 4 envelope unreadable or hashes broken.
"""


def _verify_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tessera verify",
        description=_VERIFY_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("bundle", help="path to the .tsb file to verify")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the machine-readable report instead of the human one",
    )
    parser.add_argument(
        "--require-signed",
        action="store_true",
        help="treat an unsigned bundle as a failure (exit 4)",
    )
    return parser


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """A JSON object hook that refuses duplicate keys. Standard ``json`` keeps
    last-wins, which would let a file carry a first-wins/streaming reader a
    *different* value (e.g. an injected refusal) than the verifier blesses —
    so a trust bundle must be single-valued, not merely self-consistent."""
    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r} in a trust bundle object")
        seen[key] = value
    return seen


def verify_main(argv: list[str] | None = None) -> int:
    args = _verify_parser().parse_args(argv)
    path = Path(args.bundle)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"error: cannot read {path}: {error}", file=sys.stderr)
        return 4
    try:
        bundle = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as error:
        print(
            f"error: {path} is not a well-formed trust bundle: {error}", file=sys.stderr
        )
        return 4
    if not isinstance(bundle, dict):
        print(f"error: {path} is not a JSON object", file=sys.stderr)
        return 4

    try:
        report = verify_bundle(bundle, require_signed=args.require_signed)
    except BundleFormatError as error:
        print(f"error: {error}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_report(report, source=str(path)))
    return report.exit_code
