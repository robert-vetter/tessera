"""The faithfulness verifier — deterministic, and provably able to fail.

``is_supported`` decides whether one claim's content is actually backed by its
cited evidence, by claim shape (snippet/clause containment, aggregate
recomputation, count verification, refuse-to-sum condition). It is the core of the
faithfulness metric (ADR 0005): a claim that asserts anything its citations do not
support returns ``False``, so faithfulness can — and is tested to — drop below 1.0.
No LLM; pure deterministic checks.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from tessera.graph import Node
from tessera.grounding import Claim
from tessera.resolution import normalize

_MONEY = re.compile(r"\b([A-Z]{3}) ([\d,]+\.\d{2})\b")
_COUNTS = re.compile(
    r"spanning (\d+) customer record\(s\) and (\d+) address record\(s\)"
)
_REFUSE = re.compile(r"Refused to sum across (\w+) and (\w+)")


def is_supported(claim: Claim, nodes: Mapping[str, Node]) -> bool:
    """True iff the claim's content is deterministically backed by its citations.

    ``nodes`` maps a record id to its graph node, so aggregate/count claims can be
    re-checked against the structured attributes of exactly the cited rows.
    """
    text = claim.text

    # 1) Surfaced snippet / document clause: the claim text appears in a cited record.
    needle = normalize(text)
    if needle and any(needle in normalize(rec.text) for rec in claim.support):
        return True

    # 2) Aggregate: the stated amount must recompute from exactly the cited rows.
    money = _MONEY.search(text)
    if money and "net order value" in text.lower():
        currency, raw = money.group(1), money.group(2)
        try:
            stated = Decimal(raw.replace(",", ""))
        except InvalidOperation:
            return False
        cited = [nodes.get(rec.id) for rec in claim.support]
        if cited and all(
            n is not None and n.attr("currency") == currency for n in cited
        ):
            total = sum(
                (Decimal(n.attr("net_amount") or "0") for n in cited if n), Decimal("0")
            )
            if total == stated:
                return True

    # 3) Identity/count: asserted record counts must match the cited records.
    counts = _COUNTS.search(text)
    if counts:
        want_customers, want_addresses = int(counts.group(1)), int(counts.group(2))
        kinds = [nodes[rec.id].kind for rec in claim.support if rec.id in nodes]
        if (
            kinds.count("I_Customer") == want_customers
            and kinds.count("I_AddrOrgNamePostalAddress") == want_addresses
        ):
            return True

    # 4) Refuse-to-sum: the cited rows must actually span the named currencies.
    refuse = _REFUSE.search(text)
    if refuse:
        named = {refuse.group(1), refuse.group(2)}
        cited_currencies = {
            nodes[rec.id].attr("currency")
            for rec in claim.support
            if rec.id in nodes and nodes[rec.id].attr("currency")
        }
        if named <= cited_currencies:
            return True

    return False
