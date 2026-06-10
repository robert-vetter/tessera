"""The business vertical's claim grammars, owned where they are spoken.

Relocated logic-identical from ``eval/metrics.py`` (spec 0038 / ADR 0011):
these six shapes verify the claims only the business answer paths compose —
aggregate recomputation, customer/address count matching, the renewal-date
conflict disclosure, refuse-to-sum, and the compare/superlative conclusions.
Each is a :data:`tessera.eval.metrics.ClaimShape`: it returns an **owned
verdict** (``bool``) when the claim speaks its grammar and ``None`` when it
does not, so the verifier core never needs to know any business vocabulary.
The business battery declares them in :data:`BUSINESS_CLAIM_SHAPES`
(consumed by ``tessera.eval.registry``); the adversarial tests that prove a
1.0 is earned, not tautological, live with them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from tessera.business.conflicts import renewal_date_of
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


# --- the ClaimShape functions (tri-state: bool = owned verdict, None = pass) -----


def compare_conclusion(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """A compare conclusion is recomputed over the graph's entities (spec 0019)."""
    if graph is not None and _COMPARE.search(claim.text):
        return _verify_compare(claim, graph)
    return None


def superlative_conclusion(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """A superlative conclusion is recomputed over the WHOLE graph (spec 0019)."""
    if graph is not None and _SUPERLATIVE.search(claim.text):
        return _verify_superlative(claim, graph)
    return None


def conflict_disclosure(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """A conflict disclosure must quote values really stated by DISTINCT cited
    clauses, and the values must actually disagree (spec 0021)."""
    if "disagree on the renewal date" not in claim.text:
        return None
    quoted = re.findall(r"'(\d{1,2} [A-Z][a-z]+)'", claim.text)
    cited_dates = {date for rec in claim.support if (date := renewal_date_of(rec))}
    return (
        len(set(quoted)) >= 2 and set(quoted) == cited_dates and len(claim.support) >= 2
    )


def aggregate_recompute(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """A stated total net order value must recompute from exactly the cited rows."""
    money = _MONEY.search(claim.text)
    if not (money and "net order value" in claim.text.lower()):
        return None
    currency, raw = money.group(1), money.group(2)
    stated = _dec(raw)
    if stated is None:
        return False
    cited = [nodes.get(rec.id) for rec in claim.support]
    if cited and all(n is not None and n.attr("currency") == currency for n in cited):
        total = sum(
            (Decimal(n.attr("net_amount") or "0") for n in cited if n), Decimal("0")
        )
        if total == stated:
            return True
    return None  # not verified as an aggregate; no other grammar is claimed


def count_match(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """Asserted customer/address record counts must match the cited records."""
    counts = _COUNTS.search(claim.text)
    if not counts:
        return None
    want_customers, want_addresses = int(counts.group(1)), int(counts.group(2))
    kinds = [nodes[rec.id].kind for rec in claim.support if rec.id in nodes]
    if (
        kinds.count("I_Customer") == want_customers
        and kinds.count("I_AddrOrgNamePostalAddress") == want_addresses
    ):
        return True
    return None


def refuse_to_sum(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """A refuse-to-sum disclosure: the cited rows must actually span the named
    currencies."""
    refuse = _REFUSE.search(claim.text)
    if not refuse:
        return None
    named = {refuse.group(1), refuse.group(2)}
    cited_currencies = {
        nodes[rec.id].attr("currency")
        for rec in claim.support
        if rec.id in nodes and nodes[rec.id].attr("currency")
    }
    if named <= cited_currencies:
        return True
    return None


# The business battery's declared grammar surface, in precedence order:
# conclusions first (they own their verdicts), then the computational checks
# that may yield to the generic grammars when unverified (spec 0038).
BUSINESS_CLAIM_SHAPES = (
    compare_conclusion,
    superlative_conclusion,
    conflict_disclosure,
    aggregate_recompute,
    count_match,
    refuse_to_sum,
)
