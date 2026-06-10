"""Synthetic eval scenarios, enumerated from the graph (ADR 0007).

Deterministic — no RNG, no LLM, nothing committed: cases are derived from the
graph's content at eval time. **Expectations come from the data** (record ids;
totals re-derived with Decimal arithmetic from node attributes), never from
running the engine; the engine's name matcher appears only as a
*well-posedness filter* so inherently ambiguous questions (e.g. the
deliberately unresolved Globex variant family) are not generated as answerable
cases. Gold remains the human-checked anchor; this battery measures scale.
"""

from __future__ import annotations

from decimal import Decimal

from tessera.eval.harness import GoldCase
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase
from tessera.reasoning import find_named_entities
from tessera.retrieval import _tokenize

# Questions whose content tokens must be absent from the corpus — the
# missing-evidence refusals. The generator verifies absence against the actual
# corpus vocabulary before emitting (data-derived, not engine-derived).
_MISSING_EVIDENCE_TEMPLATES = (
    "What colour is the sky?",
    "Do we operate a zeppelin fleet?",
    "Which volcano permits were filed?",
)


def _display(names: list[str | None]) -> str:
    return max((n for n in names if n), key=lambda n: (len(n), n))


def _entities(graph: KnowledgeGraph) -> list[tuple[str, frozenset[str]]]:
    """(display name, cluster) for every named entity, deterministically ordered."""
    out: list[tuple[str, frozenset[str]]] = []
    for cluster in graph.clusters():
        names = [graph.node(nid).name for nid in cluster if graph.node(nid).name]
        if names:
            out.append((_display(names), cluster))
    out.sort(key=lambda item: item[0])
    return out


def _sales(graph: KnowledgeGraph, cluster: frozenset[str]) -> list[Node]:
    ids = set(graph.sources_of(set(cluster), "sold_to"))
    return sorted((graph.node(nid) for nid in ids), key=lambda n: n.id)


def _total(rows: list[Node]) -> Decimal:
    return sum((Decimal(n.attr("net_amount") or "0") for n in rows), Decimal("0"))


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _names_exactly(
    question: str, graph: KnowledgeGraph, clusters: set[frozenset[str]]
) -> bool:
    """Well-posedness filter: the question names exactly these entities."""
    found = {e.cluster for e in find_named_entities(question, graph)}
    return found == clusters


def generate_cases(graph: KnowledgeGraph, kb: KnowledgeBase) -> list[GoldCase]:
    """Enumerate the deterministic synthetic battery for the current graph."""
    cases: list[GoldCase] = []
    entities = _entities(graph)

    # --- per-entity lookups and aggregates ---------------------------------------
    for name, cluster in entities:
        customers = sorted(
            nid for nid in cluster if graph.node(nid).kind == "I_Customer"
        )
        if not customers:
            continue
        lookup_q = f"Summarise {name}."
        if _names_exactly(lookup_q, graph, {cluster}):
            cases.append(
                GoldCase(
                    id=f"syn_lookup_{customers[0]}",
                    question=lookup_q,
                    engine="route",
                    kind="answer",
                    expected_support=tuple(customers),
                    expected_facts=("is one resolved entity",),
                )
            )

        rows = _sales(graph, cluster)
        if not rows:
            continue
        agg_q = f"Summarise {name}: sales orders and totals."
        if not _names_exactly(agg_q, graph, {cluster}):
            continue
        currencies = sorted({n.attr("currency") or "?" for n in rows})
        if len(currencies) == 1:
            facts = (
                f"Total net order value across {len(rows)} order(s): "
                f"{_money(_total(rows), currencies[0])}.",
            )
        else:
            facts = (f"Refused to sum across {' and '.join(currencies)}",)
        cases.append(
            GoldCase(
                id=f"syn_aggregate_{customers[0]}",
                question=agg_q,
                engine="route",
                kind="answer",
                expected_support=tuple(n.id for n in rows),
                expected_facts=facts,
            )
        )

    # --- multi-step: consecutive same-currency pairs ------------------------------
    per_currency: dict[str, list[tuple[Decimal, str, frozenset[str], list[Node]]]] = {}
    for name, cluster in entities:
        rows = _sales(graph, cluster)
        row_currencies = {n.attr("currency") for n in rows}
        if len(row_currencies) != 1:
            continue  # mixed or no sales: not comparable as a whole entity
        (currency,) = row_currencies
        if currency is None:
            continue
        per_currency.setdefault(currency, []).append(
            (_total(rows), name, cluster, rows)
        )

    for currency in sorted(per_currency):
        ranking = sorted(per_currency[currency], key=lambda t: (-t[0], t[1]))
        for (hi_t, hi_n, hi_c, hi_r), (lo_t, lo_n, lo_c, lo_r) in zip(
            ranking, ranking[1:], strict=False
        ):
            if hi_t == lo_t:
                continue  # 'exceeds' would be false; skip honest ties
            question = f"Compare {hi_n} and {lo_n}: total order value."
            if not _names_exactly(question, graph, {hi_c, lo_c}):
                continue
            cases.append(
                GoldCase(
                    id=f"syn_compare_{currency}_{hi_n}_{lo_n}".replace(" ", "_"),
                    question=question,
                    engine="route",
                    kind="answer",
                    expected_support=tuple(n.id for n in (*hi_r, *lo_r)),
                    expected_facts=(
                        "exceeds",
                        _money(hi_t, currency),
                        _money(lo_t, currency),
                    ),
                )
            )

        # Superlative per currency: winner re-derived from data. NOTE the ranking
        # here includes every entity with ANY rows in this currency (mixed-currency
        # entities contribute their rows of this currency), matching the engine's
        # contract — recompute accordingly.
        cases.extend(_superlative_case(graph, currency, entities))

    # --- refusals ------------------------------------------------------------------
    cases.append(
        GoldCase(
            id="syn_refuse_unscoped_superlative",
            question="Which entity has the highest total order value overall?",
            engine="route",
            kind="refuse",
        )
    )
    cases.extend(_ambiguous_token_cases(graph, entities))
    vocabulary = {token for record in kb.records for token in _tokenize(record.text)}
    for index, template in enumerate(_MISSING_EVIDENCE_TEMPLATES, start=1):
        if any(token in vocabulary for token in _tokenize(template)):
            continue  # a content token exists in the corpus: not a missing case
        cases.append(
            GoldCase(
                id=f"syn_refuse_missing_{index}",
                question=template,
                engine="route",
                kind="refuse",
            )
        )

    cases.sort(key=lambda c: c.id)
    return cases


def _superlative_case(
    graph: KnowledgeGraph,
    currency: str,
    entities: list[tuple[str, frozenset[str]]],
) -> list[GoldCase]:
    ranked: list[tuple[Decimal, str, list[Node]]] = []
    for name, cluster in entities:
        rows = [n for n in _sales(graph, cluster) if n.attr("currency") == currency]
        if rows:
            ranked.append((_total(rows), name, rows))
    if not ranked:
        return []
    ranked.sort(key=lambda t: (-t[0], t[1]))
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return []  # tied top: 'the highest' is ill-posed; skip honestly
    total, name, rows = ranked[0]
    return [
        GoldCase(
            id=f"syn_superlative_{currency}",
            question=f"Which entity has the highest total order value in {currency}?",
            engine="route",
            kind="answer",
            expected_support=tuple(n.id for n in rows),
            expected_facts=(f"'{name}'", _money(total, currency), "highest"),
        )
    ]


def _ambiguous_token_cases(
    graph: KnowledgeGraph, entities: list[tuple[str, frozenset[str]]]
) -> list[GoldCase]:
    """Bare name tokens shared by >=2 entities: asking by token alone is
    inherently ambiguous and must be refused (engine pinned to compose, like
    gold case 05)."""
    token_owners: dict[str, set[str]] = {}
    for name, _cluster in entities:
        for word in name.split():
            token = word.lower().strip(".,&")
            if len(token) >= 6:
                token_owners.setdefault(token, set()).add(name)
    shared = sorted(t for t, owners in token_owners.items() if len(owners) >= 2)
    return [
        GoldCase(
            id=f"syn_refuse_ambiguous_{token}",
            question=token.capitalize(),
            engine="compose",
            kind="refuse",
        )
        for token in shared
    ]
