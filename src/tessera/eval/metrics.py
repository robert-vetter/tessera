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

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Claim
from tessera.resolution import normalize

_MONEY = re.compile(r"\b([A-Z]{3}) ([\d,]+\.\d{2})\b")
_COUNTS = re.compile(
    r"spanning (\d+) customer record\(s\) and (\d+) address record\(s\)"
)
_REFUSE = re.compile(r"Refused to sum across (\w+) and (\w+)")
_COMPARE = re.compile(
    r"'(.+?)' \(([A-Z]{3}) ([\d,]+\.\d{2}) across (\d+) order\(s\)\) exceeds "
    r"'(.+?)' \(([A-Z]{3}) ([\d,]+\.\d{2}) across (\d+) order\(s\)\) "
    r"in total net order value"
)
_SUPERLATIVE = re.compile(
    r"Among (\d+) entities with ([A-Z]{3}) orders, '(.+?)' has the highest "
    r"total net order value: ([A-Z]{3}) ([\d,]+\.\d{2})"
)


def _dec(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _entity_of_row(graph: KnowledgeGraph, row_id: str) -> frozenset[str] | None:
    """The resolved entity a sales row was sold to (via its sold_to edge)."""
    for edge in graph.edges:
        if edge.src == row_id and edge.relation == "sold_to":
            return graph.entity_of(edge.dst)
    return None


def _cluster_names(graph: KnowledgeGraph, cluster: frozenset[str]) -> set[str]:
    return {
        normalize(name) for nid in cluster if (name := graph.node(nid).name) is not None
    }


def _verify_compare(claim: Claim, graph: KnowledgeGraph) -> bool:
    """Recompute a compare conclusion: each side's cited rows must belong to the
    named entity, sum to the stated amount in the stated currency, match the
    stated count — and the direction must hold."""
    match = _COMPARE.search(claim.text)
    assert match is not None
    sides = (
        (match.group(1), match.group(2), match.group(3), match.group(4)),
        (match.group(5), match.group(6), match.group(7), match.group(8)),
    )
    totals: list[Decimal] = []
    for name, currency, raw, count in sides:
        stated = _dec(raw)
        if stated is None:
            return False
        wanted = normalize(name)
        rows = []
        for rec in claim.support:
            entity = _entity_of_row(graph, rec.id)
            if entity is not None and wanted in _cluster_names(graph, entity):
                rows.append(graph.node(rec.id))
        if len(rows) != int(count):
            return False
        if any(n.attr("currency") != currency for n in rows):
            return False
        total = sum((Decimal(n.attr("net_amount") or "0") for n in rows), Decimal("0"))
        if total != stated:
            return False
        totals.append(total)
    return totals[0] > totals[1]


def _verify_superlative(claim: Claim, graph: KnowledgeGraph) -> bool:
    """Recompute a superlative conclusion over the WHOLE graph: the stated
    entity count, winner, and amount must all re-derive from the data."""
    match = _SUPERLATIVE.search(claim.text)
    assert match is not None
    stated_count = int(match.group(1))
    currency = match.group(2)
    winner = normalize(match.group(3))
    if match.group(4) != currency:
        return False
    stated = _dec(match.group(5))
    if stated is None:
        return False

    ranked: list[tuple[Decimal, frozenset[str]]] = []
    for cluster in graph.clusters():
        if not _cluster_names(graph, cluster):
            continue
        rows = [
            graph.node(nid)
            for nid in set(graph.sources_of(set(cluster), "sold_to"))
            if graph.node(nid).attr("currency") == currency
        ]
        if not rows:
            continue
        total = sum((Decimal(n.attr("net_amount") or "0") for n in rows), Decimal("0"))
        ranked.append((total, cluster))
    if len(ranked) != stated_count or not ranked:
        return False
    best_total, best_cluster = max(ranked, key=lambda item: item[0])
    if best_total != stated or winner not in _cluster_names(graph, best_cluster):
        return False
    # Bind the citation: the cited rows themselves must sum to the stated total.
    cited = [nodes_n for rec in claim.support if (nodes_n := graph.node(rec.id))]
    cited_total = sum(
        (Decimal(n.attr("net_amount") or "0") for n in cited), Decimal("0")
    )
    return cited_total == stated and all(n.attr("currency") == currency for n in cited)


def is_supported(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None = None
) -> bool:
    """True iff the claim's content is deterministically backed by its citations.

    ``nodes`` maps a record id to its graph node, so aggregate/count claims can be
    re-checked against the structured attributes of exactly the cited rows.
    ``graph`` (optional) enables the multi-step shapes — compare and superlative
    conclusions are recomputed over the graph's entities (spec 0019).
    """
    text = claim.text

    # 5) Multi-step conclusions (compare / superlative): need the graph.
    if graph is not None:
        if _COMPARE.search(text):
            return _verify_compare(claim, graph)
        if _SUPERLATIVE.search(text):
            return _verify_superlative(claim, graph)

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
