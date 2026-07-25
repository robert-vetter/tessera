#!/usr/bin/env python3
"""Build the cross-implementation conformance kit (spec 0148).

Every case is materialised deterministically from committed code — the
committed artifacts crossed with the CI-pinned attack battery — so the kit
costs bytes rather than megabytes and can never drift from the generators
it describes. The committed `data/kit/expectations.json` records, per case,
the reference verifier's exit code and the independent verifier's verdict;
a test pins the file byte-identical to a fresh run.

Run: `uv run python scripts/build_conformance_kit.py`
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.verify import BundleFormatError, verify_bundle
from tessera.conformance.attacks import ATTACKS, base_bundles

REPO = Path(__file__).resolve().parents[1]
KIT = REPO / "data" / "kit" / "expectations.json"
JS_VERIFIER = REPO / "verifier" / "js" / "tessera-verify.mjs"


#: Substrings that identify a reference-verifier failure whose *cause* is one
#: of the two checks the independent verifier cannot perform: re-running the
#: domain router (answer re-derivation) or the drafting pipeline (action
#: re-derivation). Both need the engine, so a portable verifier can only
#: decline them — and must say so rather than pass them silently.
NON_PORTABLE_CAUSES = (
    "does not re-derive the recorded answer",
    "recorded refusal reason does not re-derive",
    "recorded claims are not the answer",
    "route or verdict metadata diverges",
    "a derived field in the recorded result",
    "wire method/path",
    "wire body",
    "wire slots",
    "execution outcome",
    "action receipt does not match",
    "unapproved",
    "claims a real send",
    "action records a different domain/question",
)


def python_report(bundle: dict[str, object]) -> tuple[int, tuple[str, ...]]:
    """The reference verifier's exit code and its named semantic problems."""
    try:
        report = verify_bundle(bundle)
    except BundleFormatError:
        return 4, ()
    return report.exit_code, report.semantic_problems


def portable_blind_spot(problems: tuple[str, ...]) -> bool:
    """True when every named failure is one the portable verifier declines by
    design (rather than one it should have caught)."""
    return bool(problems) and all(
        any(marker in problem for marker in NON_PORTABLE_CAUSES) for problem in problems
    )


def js_report(bundle: dict[str, object]) -> Any:
    """Run the independent verifier out-of-process on a materialised file."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "case.tsb"
        path.write_bytes(canonical_bytes(bundle) + b"\n")
        proc = subprocess.run(
            ["node", str(JS_VERIFIER), str(path), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
    if not proc.stdout.strip():
        raise RuntimeError(
            f"the independent verifier produced no output: {proc.stderr}"
        )
    report = json.loads(proc.stdout)
    report["exit_code"] = proc.returncode
    return report


def cases() -> list[dict[str, object]]:
    """The committed artifacts (honest baselines) plus every attack."""
    bases = base_bundles()
    out: list[dict[str, object]] = []

    for name, bundle in sorted(bases.items()):
        out.append(
            {"case": f"honest:{name}", "base": name, "attack": None, "bundle": bundle}
        )
    for attack in ATTACKS:
        out.append(
            {
                "case": f"attack:{attack.key}",
                "base": attack.base,
                "attack": attack.key,
                "bundle": attack.forge(bases[attack.base]),
            }
        )
    return out


def build() -> Any:
    entries = []
    for case in cases():
        bundle = case.pop("bundle")
        assert isinstance(bundle, dict)
        report = js_report(bundle)
        claims = report.get("claims")
        exit_code, problems = python_report(bundle)
        verdict = report["verdict"]
        entries.append(
            {
                **case,
                "python_exit": exit_code,
                "js_verdict": verdict,
                "js_exit": report["exit_code"],
                "js_claims_evaluated": (
                    sum(1 for c in claims if c.get("rederived") is not None)
                    if isinstance(claims, list)
                    else 0
                ),
                # Only meaningful when the reference fails and the portable
                # verifier does not: it records WHY that is legitimate.
                "declined_by_design": bool(
                    verdict == "PASS-PARTIAL"
                    and exit_code == 2
                    and portable_blind_spot(problems)
                ),
            }
        )
    caught = sum(1 for e in entries if e["js_verdict"] in ("FAIL", "TAMPERED"))
    declined = sum(1 for e in entries if e["declined_by_design"])
    return {
        "kit": "tessera-cross-implementation-1",
        "reference": "tessera.bundle.verify (Python)",
        "independent": "verifier/js/tessera-verify.mjs (JavaScript, zero deps)",
        "contract": [
            "js TAMPERED implies python exit 4",
            "js FAIL implies python exit 2 or 4 — the portable verifier never "
            "rejects what the reference accepts",
            "js PASS-PARTIAL with python exit 2 is allowed ONLY when every named "
            "reference failure is one of the two checks the portable verifier "
            "cannot perform (answer or action re-derivation); it declines them "
            "openly rather than passing them silently",
        ],
        "summary": {
            "cases": len(entries),
            "caught_by_both": caught,
            "declined_by_design": declined,
        },
        "cases": entries,
    }


def main() -> int:
    if not JS_VERIFIER.is_file():
        print(f"error: {JS_VERIFIER} is missing", file=sys.stderr)
        return 1
    payload = build()
    KIT.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(payload) + b"\n"
    KIT.write_bytes(data)
    agree = sum(1 for c in payload["cases"] if c["js_verdict"] != "NOT-EVALUABLE")
    print(f"wrote {KIT.relative_to(REPO)} ({len(data):,} bytes)")
    print(f"cases: {len(payload['cases'])}, judged by both implementations: {agree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
