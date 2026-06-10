"""Multi-step reasoning over the knowledge graph: compare and superlative.

The two deterministic multi-step shapes Phase 2 adds (spec 0019, ADR 0006):

- **Compare** two named entities' total net order value — per-entity sourced
  step claims plus a conclusion claim citing both row sets.
- **Superlative** — which entity has the highest total net order value in an
  explicitly named currency, ranking per-entity totals over that currency's
  rows only.

Honesty rules: totals are computed from, and cited to, exactly the rows they
sum; nothing is ranked or compared across currencies (that would be silent
source mixing — the project's #1 failure mode); when entities are not
comparable, or no currency scope is given, the engine **refuses with the
reason** instead of guessing. No LLM, no NLU — name-containment entity finding
and arithmetic recomposition, with refusal as the boundary of competence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Answer, Claim
from tessera.resolution import normalize

# An entity is "named" by the question when the longest common run with one of
# its names covers >= this fraction of the (normalized) name...
NAME_MATCH_RATIO = 0.6
# ... and is at least this many characters (so generic tokens like "logistik"
# alone cannot sweep in every firm sharing them).
MIN_NAME_MATCH = 6

_SUPERLATIVE_WORDS = ("highest", "largest", "biggest", "most", "top")
_CURRENCY = re.compile(r"\b([A-Z]{3})\b")

NOT_MULTI_REFUSAL = (
    "I can't treat this as a multi-step question (compare two named entities, "
    "or ask for the highest total in a named currency)."
)


@dataclass(frozen=True)
class _Entity:
    """A resolved entity, as multi-step reasoning sees it."""

    cluster: frozenset[str]
    name: str  # display name (most complete member name)
    match: int  # longest common run with the question


def _display(names: list[str | None]) -> str:
    """The most complete member name, with a DETERMINISTIC tie-break.

    ``(len, n)`` matters: equal-length variants (e.g. 'GmbH' vs 'GMBH') would
    otherwise be chosen by frozenset iteration order, which is hash-seeded and
    differs between processes — a real flake this codebase has met."""
    return max((n for n in names if n), key=lambda n: (len(n), n))


def _longest_common(a: str, b: str) -> int:
    if not a or not b:
        return 0
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size


def find_named_entities(question: str, graph: KnowledgeGraph) -> list[_Entity]:
    """Entities the question names, by relative-threshold name containment.

    Requiring the match to cover most of the *name* (not just a long absolute
    run) keeps shared suffixes/tokens from matching every similar firm.
    Deterministic: ordered by match length desc, then name.
    """
    q = normalize(question)
    found: list[_Entity] = []
    for cluster in graph.clusters():
        names = [graph.node(nid).name for nid in cluster if graph.node(nid).name]
        if not names:
            continue
        best = 0
        for name in names:
            assert name is not None
            norm = normalize(name)
            run = _longest_common(q, norm)
            if run >= MIN_NAME_MATCH and run / len(norm) >= NAME_MATCH_RATIO:
                best = max(best, run)
        if best:
            display = _display(names)
            found.append(_Entity(cluster=cluster, name=display, match=best))
    found.sort(key=lambda e: (-e.match, e.name))
    return found


def _sales_of(graph: KnowledgeGraph, entity: _Entity) -> list[Node]:
    ids = set(graph.sources_of(set(entity.cluster), "sold_to"))
    return sorted((graph.node(nid) for nid in ids), key=lambda n: n.id)


def _totals_by_currency(sales: list[Node]) -> dict[str, tuple[Decimal, list[Node]]]:
    grouped: dict[str, list[Node]] = {}
    for node in sales:
        grouped.setdefault(node.attr("currency") or "?", []).append(node)
    return {
        currency: (
            sum((Decimal(n.attr("net_amount") or "0") for n in nodes), Decimal("0")),
            nodes,
        )
        for currency, nodes in grouped.items()
    }


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _step_claim(name: str, currency: str, total: Decimal, rows: list[Node]) -> Claim:
    return Claim(
        text=(
            f"'{name}': total net order value across {len(rows)} order(s): "
            f"{_money(total, currency)}."
        ),
        support=tuple(n.record for n in rows),
    )


def compare(question: str, a: _Entity, b: _Entity, graph: KnowledgeGraph) -> Answer:
    """Compare two entities' totals — or refuse when they are not comparable."""
    totals = [_totals_by_currency(_sales_of(graph, e)) for e in (a, b)]
    for entity, t in zip((a, b), totals, strict=True):
        if not t:
            return Answer(
                question=question,
                claims=(),
                refusal=(
                    f"No sales orders found for '{entity.name}' — nothing to compare."
                ),
            )
        if len(t) > 1:
            currencies = " and ".join(sorted(t))
            return Answer(
                question=question,
                claims=(),
                refusal=(
                    f"Cannot compare: '{entity.name}' has orders in {currencies}, "
                    "which are not directly comparable."
                ),
            )
    (cur_a, (total_a, rows_a)) = next(iter(totals[0].items()))
    (cur_b, (total_b, rows_b)) = next(iter(totals[1].items()))
    if cur_a != cur_b:
        return Answer(
            question=question,
            claims=(),
            refusal=(
                f"Cannot compare: '{a.name}' has orders in {cur_a} but '{b.name}' "
                f"in {cur_b}; the totals are not directly comparable."
            ),
        )

    steps = [_step_claim(a.name, cur_a, total_a, rows_a)]
    steps.append(_step_claim(b.name, cur_b, total_b, rows_b))

    if total_a == total_b:
        conclusion_text = (
            f"'{a.name}' and '{b.name}' have the same total net order value: "
            f"{_money(total_a, cur_a)}."
        )
    else:
        (w_name, w_t, w_r), (l_name, l_t, l_r) = sorted(
            ((a.name, total_a, rows_a), (b.name, total_b, rows_b)),
            key=lambda x: -x[1],
        )
        conclusion_text = (
            f"'{w_name}' ({_money(w_t, cur_a)} across {len(w_r)} order(s)) exceeds "
            f"'{l_name}' ({_money(l_t, cur_a)} across {len(l_r)} order(s)) "
            "in total net order value."
        )
    conclusion = Claim(
        text=conclusion_text, support=tuple(n.record for n in (*rows_a, *rows_b))
    )
    return Answer(question=question, claims=(*steps, conclusion), refusal=None)


def superlative(question: str, graph: KnowledgeGraph) -> Answer:
    """Which entity has the highest total net order value, in a named currency."""
    scope = _CURRENCY.search(question)
    all_currencies = sorted({c for n in graph.nodes if (c := n.attr("currency"))})
    if not scope:
        return Answer(
            question=question,
            claims=(),
            refusal=(
                "A single ranking would mix currencies "
                f"({', '.join(all_currencies)}); name one (e.g. 'in EUR') and "
                "I can rank the totals honestly."
            ),
        )
    currency = scope.group(1)

    ranked: list[tuple[Decimal, str, list[Node]]] = []
    for cluster in graph.clusters():
        names = [graph.node(nid).name for nid in cluster if graph.node(nid).name]
        if not names:
            continue
        rows = [
            graph.node(nid)
            for nid in set(graph.sources_of(set(cluster), "sold_to"))
            if graph.node(nid).attr("currency") == currency
        ]
        if not rows:
            continue
        rows.sort(key=lambda n: n.id)
        total = sum((Decimal(n.attr("net_amount") or "0") for n in rows), Decimal("0"))
        display = _display(names)
        ranked.append((total, display, rows))
    if not ranked:
        return Answer(
            question=question,
            claims=(),
            refusal=f"No entity has orders in {currency}.",
        )

    ranked.sort(key=lambda item: (-item[0], item[1]))
    total, name, rows = ranked[0]
    conclusion = Claim(
        text=(
            f"Among {len(ranked)} entities with {currency} orders, '{name}' has "
            f"the highest total net order value: {_money(total, currency)}."
        ),
        support=tuple(n.record for n in rows),
    )
    return Answer(question=question, claims=(conclusion,), refusal=None)


def reason(question: str, graph: KnowledgeGraph) -> Answer:
    """Dispatch a multi-step question: compare when two entities are named,
    superlative when a ranking is asked; otherwise refuse (the router owns
    sending only multi-step questions here)."""
    entities = find_named_entities(question, graph)
    if len(entities) == 2:
        return compare(question, entities[0], entities[1], graph)
    if len(entities) > 2:
        labels = ", ".join(e.name for e in entities)
        return Answer(
            question=question,
            claims=(),
            refusal=(
                f"Ambiguous: the question matches more than two entities ({labels})."
            ),
        )
    lowered = question.lower()
    if any(word in lowered for word in _SUPERLATIVE_WORDS):
        return superlative(question, graph)
    return Answer(question=question, claims=(), refusal=NOT_MULTI_REFUSAL)
