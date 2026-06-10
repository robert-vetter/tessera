"""Cross-source answer composition over the knowledge graph (the Phase 1 payoff).

Given a question naming an organization, resolve it to a graph entity, gather that
entity's evidence across **both** sources — its structured rows (customer/address
+ sales documents via structural edges) and its document clauses (via the
mentioned document) — and compose one grounded answer whose claims trace to a row
*and* a clause.

The one synthesis it performs is a **fully-sourced** aggregate: the entity's total
net order value, summed over its sales rows with every summand cited. If the rows
are not comparable (mixed currencies) it does **not** invent a single total — it
reports per-currency subtotals and says why. General multi-step / multi-entity
reasoning and question routing remain Phase 2; this is one entity, assembled
honestly. No LLM (ADR 0003); resolution reuses the ADR-0004 matcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Answer, Claim
from tessera.resolution import normalize

# A question phrase must share at least this many characters with an entity name
# (normalized) to count as naming it — below this it is not an entity reference.
MIN_NAME_MATCH = 6

NO_ENTITY_REFUSAL = (
    "I couldn't find an entity in the knowledge graph for that question."
)


@dataclass(frozen=True)
class EntityMatch:
    """The outcome of resolving a question to an entity cluster."""

    status: str  # "ok" | "none" | "ambiguous"
    cluster: frozenset[str] = frozenset()
    candidates: tuple[str, ...] = ()


def _longest_common(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size


def _display_name(graph: KnowledgeGraph, cluster: frozenset[str]) -> str:
    """The most complete member name — a stable label for the entity."""
    names = [graph.node(nid).name for nid in cluster if graph.node(nid).name]
    # (len, n) tie-break: equal-length variants (e.g. 'GmbH' vs 'GMBH') would
    # otherwise be chosen by frozenset iteration order, which is hash-seeded
    # and therefore nondeterministic across processes.
    return max(
        (n for n in names if n), key=lambda n: (len(n), n), default="(unnamed entity)"
    )


def resolve_entity(question: str, graph: KnowledgeGraph) -> EntityMatch:
    """Resolve the question to one entity by longest normalized-name overlap.

    Best match wins; a tie between distinct entities is **refused** as ambiguous
    rather than guessed (groundedness over fluency). Deterministic.
    """
    q = normalize(question)
    scored: list[tuple[frozenset[str], int]] = []
    for cluster in graph.clusters():
        names = [graph.node(nid).name for nid in cluster if graph.node(nid).name]
        best = max((_longest_common(q, normalize(n)) for n in names if n), default=0)
        if best >= MIN_NAME_MATCH:
            scored.append((cluster, best))
    if not scored:
        return EntityMatch(status="none")

    top = max(score for _, score in scored)
    winners = [cluster for cluster, score in scored if score == top]
    if len(winners) > 1:
        labels = tuple(sorted(_display_name(graph, c) for c in winners))
        return EntityMatch(status="ambiguous", candidates=labels)
    return EntityMatch(status="ok", cluster=winners[0])


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _aggregate_claims(graph: KnowledgeGraph, sales: list[Node]) -> list[Claim]:
    """Sum net order value, fully sourced. Refuse a single total across currencies."""
    by_currency: dict[str, list[Node]] = {}
    for node in sales:
        by_currency.setdefault(node.attr("currency") or "?", []).append(node)

    def subtotal(nodes: list[Node]) -> Decimal:
        return sum((Decimal(n.attr("net_amount") or "0") for n in nodes), Decimal("0"))

    if len(by_currency) == 1:
        ((currency, nodes),) = by_currency.items()
        total = subtotal(nodes)
        text = (
            f"Total net order value across {len(nodes)} order(s): "
            f"{_money(total, currency)}."
        )
        return [Claim(text=text, support=tuple(n.record for n in nodes))]

    # Mixed currencies: no single total — per-currency subtotals + an honest note.
    claims: list[Claim] = []
    for currency in sorted(by_currency):
        nodes = by_currency[currency]
        claims.append(
            Claim(
                text=(
                    f"Net order value in {currency} across {len(nodes)} order(s): "
                    f"{_money(subtotal(nodes), currency)}."
                ),
                support=tuple(n.record for n in nodes),
            )
        )
    claims.append(
        Claim(
            text=(
                "Refused to sum across "
                f"{' and '.join(sorted(by_currency))}: the orders are in different "
                "currencies and are not directly comparable."
            ),
            support=tuple(n.record for n in sales),
        )
    )
    return claims


def compose(question: str, graph: KnowledgeGraph) -> Answer:
    """Compose a grounded, cross-source answer about one resolved entity."""
    match = resolve_entity(question, graph)
    if match.status == "none":
        return Answer(question=question, claims=(), refusal=NO_ENTITY_REFUSAL)
    if match.status == "ambiguous":
        refusal = (
            f"Ambiguous: the question matches more than one entity "
            f"({' and '.join(match.candidates)}); please disambiguate."
        )
        return Answer(question=question, claims=(), refusal=refusal)

    cluster = match.cluster
    name = _display_name(graph, cluster)
    claims: list[Claim] = []

    # 1) Identity — grounded in the entity's master records. The claim asserts
    #    both customer and address counts, so it must cite BOTH (faithfulness).
    customers = [
        graph.node(nid) for nid in cluster if graph.node(nid).kind == "I_Customer"
    ]
    addresses = [
        graph.node(nid)
        for nid in cluster
        if graph.node(nid).kind == "I_AddrOrgNamePostalAddress"
    ]
    if customers:
        claims.append(
            Claim(
                text=(
                    f"'{name}' is one resolved entity spanning {len(customers)} "
                    f"customer record(s) and {len(addresses)} address record(s)."
                ),
                support=tuple(node.record for node in (*customers, *addresses)),
            )
        )

    # 2) Sourced aggregate over the entity's sales rows.
    sales_ids = set(graph.sources_of(set(cluster), "sold_to"))
    sales = [graph.node(nid) for nid in sales_ids]
    if sales:
        claims.extend(_aggregate_claims(graph, sales))

    # 3) Document clauses — the agreement(s) associated with this entity. A mention
    #    links the chunk that names the party; the whole mentioned document is the
    #    entity's document evidence, so clauses elsewhere in it (e.g. renewal) count.
    mentioned_docs = {
        graph.node(m.chunk).record.origin.source
        for m in graph.mentions_of(set(cluster))
    }
    clause_nodes = [
        n
        for n in graph.nodes
        if n.kind == "document" and n.record.origin.source in mentioned_docs
    ]
    for node in sorted(clause_nodes, key=lambda n: n.id):
        claims.append(Claim(text=node.record.text, support=(node.record,)))

    if not claims:
        return Answer(question=question, claims=(), refusal=NO_ENTITY_REFUSAL)
    return Answer(question=question, claims=tuple(claims), refusal=None)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from tessera.knowledge import build_demo_graph

    parser = argparse.ArgumentParser(
        prog="tessera-compose",
        description=(
            "Answer one cross-source question about an organization by composing "
            "evidence from both sources over the knowledge graph. Every claim is "
            "sourced; the total is summed only over comparable rows."
        ),
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="Summarise Müller Logistik: its sales orders and agreement terms.",
        help="A question naming an organization.",
    )
    args = parser.parse_args(argv)
    print(compose(args.question, build_demo_graph()).render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
