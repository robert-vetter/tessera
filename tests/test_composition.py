"""Tests for cross-source answer composition (the Phase 1 milestone).

The two most important tests are pinned explicitly: the synthesized total equals
exactly the sum of the cited rows (no summand uncited, no row uncounted), and the
mixed-currency case refuses to produce a single total and says why.
"""

from __future__ import annotations

import re
from decimal import Decimal

from tessera.composition import compose, resolve_entity
from tessera.knowledge import build_demo_graph

MUELLER = "I_Customer:0010000007"


def test_resolves_question_to_the_right_entity() -> None:
    g = build_demo_graph()
    match = resolve_entity("What are Müller Logistik's orders?", g)
    assert match.status == "ok"
    assert MUELLER in match.cluster
    # Not the distinct firm that merely shares the "Logistik" token.
    assert "I_Customer:0010001007" not in match.cluster


def test_answer_combines_a_row_and_a_clause_across_sources() -> None:
    g = build_demo_graph()
    answer = compose("Müller Logistik sales orders and agreement terms", g)
    assert answer.is_grounded
    sources = {rec.origin.source for c in answer.claims for rec in c.support}
    assert any(s.startswith("salt_synthetic/") for s in sources)  # a database row
    assert any(s.startswith("business_docs/") for s in sources)  # a document clause
    # The agreement's renewal clause is surfaced, not just the boilerplate.
    clause_texts = " ".join(rec.text for c in answer.claims for rec in c.support)
    assert "auto-renews" in clause_texts


def test_aggregate_equals_exactly_the_cited_rows() -> None:
    """THE key test: the total is the sum of exactly its cited rows — no cited
    summand left out of the total, no entity sales row left uncited."""
    g = build_demo_graph()
    answer = compose("Müller Logistik total net order value", g)

    total_claim = next(c for c in answer.claims if c.text.startswith("Total net order"))
    match = re.search(r"EUR ([\d,]+\.\d{2})", total_claim.text)
    assert match is not None
    claimed_total = Decimal(match.group(1).replace(",", ""))

    # 1) The claimed total == sum of the net_amount of exactly the cited rows.
    cited_amounts = [
        Decimal(g.node(rec.id).attr("net_amount") or "0") for rec in total_claim.support
    ]
    assert sum(cited_amounts, Decimal("0")) == claimed_total

    # 2) The cited rows are exactly the entity's sales documents — none omitted,
    #    none extra.
    entity = resolve_entity("Müller Logistik", g).cluster
    expected = set(g.sources_of(set(entity), "sold_to"))
    cited = {rec.id for rec in total_claim.support}
    assert cited == expected


def test_mixed_currency_refuses_to_sum_and_says_why() -> None:
    g = build_demo_graph()
    answer = compose("What is Atlas Trading's total order value?", g)
    assert answer.is_grounded  # it still answers (per currency) — just no single total
    texts = [c.text for c in answer.claims]

    # No single combined total was fabricated across currencies.
    assert not any(t.startswith("Total net order value across") for t in texts)
    # The refusal is explicit and names the currencies it would not sum across.
    refusal = next(c for c in answer.claims if c.text.startswith("Refused to sum"))
    assert "EUR and USD" in refusal.text
    assert refusal.support  # the refusal still cites the conflicting rows


def test_ambiguous_question_is_refused_not_guessed() -> None:
    g = build_demo_graph()
    answer = compose("Logistik", g)  # matches Müller and Nordwind equally
    assert not answer.is_grounded
    assert "Ambiguous" in (answer.refusal or "")


def test_unmatched_question_is_refused() -> None:
    g = build_demo_graph()
    answer = compose("What colour is the sky?", g)
    assert not answer.is_grounded
    assert answer.refusal
