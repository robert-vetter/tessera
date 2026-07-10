#!/usr/bin/env python3
"""The FOIL: what integrity-only verification sees (spec 0134, docs/BUNDLE.md).

This is deliberately the whole of what signature/hash-chain-style receipt
verification checks — the market default (spec 0131's prior-art finding):
recompute every leaf hash and the root, and call the file good if they
match. It proves the file is the file. It proves NOTHING about whether the
content is true: tamper a packaged record, re-seal (recompute the manifest
and root), and this checker prints INTACT while ``tessera verify`` re-runs
the verification and names the broken claim.

Run it beside ``tessera verify`` on the same re-sealed tampered bundle —
that contrast is the point of the whole act.
"""

from __future__ import annotations

import json
import sys

from tessera.bundle.format import integrity_mismatches


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: foil_integrity_only.py <bundle.tsb>", file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding="utf-8") as handle:
        bundle = json.load(handle)
    problems = integrity_mismatches(bundle)
    if problems:
        print("TAMPERED — " + "; ".join(problems))
        return 1
    print("INTACT — every hash checks out. (Nothing here checked the content.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
