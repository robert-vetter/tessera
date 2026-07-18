#!/usr/bin/env python3
"""Build the committed chain demo: one brief over two verified receipts (spec 0143).

Deterministic and committed, like the challenge pair: anyone can re-run this
and confirm the committed `data/chain/brief.tsb` is exactly what the script
produces (a test pins byte-identity). The brief chains two upstream trust
bundles across two verticals:

- a fresh DevEx root-cause receipt for the failed run R-1042, and
- the challenge's committed **honest** business bundle
  (`data/challenge/honest.tsb`, the Müller/Nordwind comparison),

and answers one question by *citing* their verifier-passing claims. The
upstreams travel embedded, so `tessera verify data/chain/brief.tsb`
re-executes the whole chain — both upstream re-verifications and the brief's
own answer — offline, from the one file.

Run: `uv run python scripts/build_chain_demo.py` (rewrites the committed
brief; the test pins that the committed file matches a fresh run).
"""

from __future__ import annotations

import json
from pathlib import Path

from tessera.bundle.chain import build_chain_bundle
from tessera.bundle.emit import build_bundle, bundle_bytes, write_bundle

REPO = Path(__file__).resolve().parents[1]
CHAIN_DIR = REPO / "data" / "chain"
HONEST = REPO / "data" / "challenge" / "honest.tsb"

RCA_QUESTION = "Why did run R-1042 fail, and has this happened before?"
QUESTION = (
    "What do the verified receipts establish about the run R-1042 failure "
    "and the Müller Logistik and Nordwind Logistik totals?"
)


def build_brief() -> dict[str, object]:
    """The demo brief: a fresh devex RCA bundle + the committed honest
    challenge bundle, chained. Emission re-verifies both (spec 0143 D1)."""
    rca = json.loads(bundle_bytes(build_bundle("devex", RCA_QUESTION)))
    totals = json.loads(HONEST.read_text(encoding="utf-8"))
    return build_chain_bundle([rca, totals], QUESTION)


def main() -> None:
    brief = build_brief()
    CHAIN_DIR.mkdir(parents=True, exist_ok=True)
    size = write_bundle(brief, CHAIN_DIR / "brief.tsb")
    integrity = brief["integrity"]
    assert isinstance(integrity, dict)
    print(f"wrote data/chain/brief.tsb ({size:,} bytes)")
    print(f"root: {integrity['root']}")


if __name__ == "__main__":
    main()
