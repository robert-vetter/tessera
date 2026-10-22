#!/usr/bin/env python3
"""Build the challenge pair: an honest bundle and a perfect forgery (spec 0140).

Deterministic and committed, so the forgery hides nothing — anyone can re-run
this and confirm exactly how the fake was made. The honest bundle answers a
question over the **synthetic** business corpus (no SALT-derived values, ever).
The forgery is derived from it by a single documented edit — inflating the
*stated conclusion* of the Nordwind total by EUR 3,500 across every claim that
cites it, while leaving every cited evidence row **untouched** — then
re-sealed so its hash chain is valid.

The result is the honest hard case: not a garbled file, but a confident,
well-cited, *wrong* answer — exactly what an ungated agent produces. Every
signature-style verifier passes it (the foil reports INTACT); only re-summing
the cited rows exposes the lie. `tessera verify data/challenge/forged.tsb`
fails it, naming the broken claims.

Run: `uv run python scripts/forge_challenge_bundle.py` (rewrites the committed
pair; a test pins that the committed files are byte-identical to a fresh run).
"""

from __future__ import annotations

import copy
import re
from decimal import Decimal
from pathlib import Path

from tessera.bundle.emit import build_bundle, write_bundle
from tessera.bundle.format import seal

QUESTION = "Compare Müller Logistik and Nordwind Logistik totals."
DOMAIN = "business"
# The single, documented edit: inflate the Nordwind total by this much.
INFLATION = Decimal("3500.00")

CHALLENGE_DIR = Path(__file__).resolve().parents[1] / "data" / "challenge"
_MONEY = re.compile(r"EUR ([\d,]+\.\d{2})")


def _fmt(amount: Decimal) -> str:
    """Format a Decimal the way the engine renders money: thousands commas,
    two decimals (e.g. ``88,000.00``)."""
    return f"{amount:,.2f}"


def build_honest() -> dict[str, object]:
    return build_bundle(DOMAIN, QUESTION)


def forge(honest: dict[str, object]) -> dict[str, object]:
    """Derive the forgery: inflate the stated Nordwind total everywhere it
    appears in the claims, leave the evidence untouched, re-seal."""
    forged = copy.deepcopy(honest)
    result = forged["result"]
    assert isinstance(result, dict)
    claims = result["claims"]
    assert isinstance(claims, list)

    # The honest Nordwind total is the amount in the first claim.
    first = claims[0]
    assert isinstance(first, dict)
    match = _MONEY.search(str(first["text"]))
    assert match is not None, "expected a EUR amount in the first claim"
    honest_amount = Decimal(match.group(1).replace(",", ""))
    forged_amount = honest_amount + INFLATION
    honest_str = f"EUR {_fmt(honest_amount)}"
    forged_str = f"EUR {_fmt(forged_amount)}"

    for claim in claims:
        assert isinstance(claim, dict)
        claim["text"] = str(claim["text"]).replace(honest_str, forged_str)
        # The evidence (support) is deliberately NOT touched — the lie is in
        # the conclusion, not the records it cites.

    unsealed = {key: value for key, value in forged.items() if key != "integrity"}
    return seal(unsealed)


def main() -> int:
    CHALLENGE_DIR.mkdir(parents=True, exist_ok=True)
    honest = build_honest()
    forged = forge(honest)
    honest_bytes = write_bundle(honest, CHALLENGE_DIR / "honest.tsb")
    forged_bytes = write_bundle(forged, CHALLENGE_DIR / "forged.tsb")
    print(f"wrote data/challenge/honest.tsb ({honest_bytes:,} bytes)")
    print(f"wrote data/challenge/forged.tsb ({forged_bytes:,} bytes)")
    print("the forgery inflates the Nordwind total by EUR 3,500; evidence untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
