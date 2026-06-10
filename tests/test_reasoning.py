"""Multi-step reasoning: compare + superlative, with faithfulness in lockstep.

The numbers asserted here are exact properties of the deterministic demo data
(data/salt_synthetic): Nordwind EUR 84,500 > Müller EUR 77,500; the EUR
superlative is Orion Datentechnik at EUR 197,500 among 13 EUR entities. If the
data generator changes, these change loudly — that is intended.
"""

import pytest

from tessera.business.claims import BUSINESS_CLAIM_SHAPES
from tessera.business.knowledge import build_demo_graph
from tessera.business.reasoning import NOT_MULTI_REFUSAL, find_named_entities, reason
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph
from tessera.grounding import Claim


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_demo_graph()


def _nodes(graph: KnowledgeGraph) -> dict[str, object]:
    return {node.id: node for node in graph.nodes}


# --- entity finding -------------------------------------------------------------


def test_find_two_named_entities(graph: KnowledgeGraph) -> None:
    found = find_named_entities(
        "Compare Müller Logistik with Nordwind Logistik on order value.", graph
    )
    names = {e.name for e in found}
    assert names == {"Mueller Logistik Gmbh", "Nordwind Logistik GmbH"}


def test_generic_token_does_not_match(graph: KnowledgeGraph) -> None:
    """'logistik' alone covers too little of any name to count as naming it."""
    assert find_named_entities("What about logistik in general?", graph) == []


# --- compare --------------------------------------------------------------------


def test_compare_is_grounded_and_correct(graph: KnowledgeGraph) -> None:
    answer = reason(
        "Compare Müller Logistik with Nordwind Logistik: total order value.", graph
    )
    assert answer.is_grounded
    rendered = answer.render()
    # Per-entity steps and the conclusion, with the true direction.
    assert (
        "'Mueller Logistik Gmbh': total net order value across 5 order(s)" in rendered
    )
    assert (
        "'Nordwind Logistik GmbH': total net order value across 3 order(s)" in rendered
    )
    assert "EUR 84,500.00" in rendered and "EUR 77,500.00" in rendered
    assert "exceeds 'Mueller Logistik Gmbh'" in rendered


def test_compare_claims_pass_faithfulness(graph: KnowledgeGraph) -> None:
    answer = reason("Compare Müller Logistik and Nordwind Logistik totals.", graph)
    nodes = {node.id: node for node in graph.nodes}
    assert answer.claims
    assert all(
        is_supported(claim, nodes, graph, BUSINESS_CLAIM_SHAPES)
        for claim in answer.claims
    )


def test_compare_refuses_across_currencies(graph: KnowledgeGraph) -> None:
    answer = reason("Compare Maple Leaf Mining and Müller Logistik totals.", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "EUR" in answer.refusal and "CAD" in answer.refusal


def test_compare_refuses_mixed_currency_entity(graph: KnowledgeGraph) -> None:
    answer = reason("Compare Atlas Trading and Müller Logistik totals.", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "Atlas Trading GmbH" in answer.refusal


# --- superlative ----------------------------------------------------------------


def test_superlative_in_eur(graph: KnowledgeGraph) -> None:
    answer = reason("Which entity has the highest total order value in EUR?", graph)
    assert answer.is_grounded
    (claim,) = answer.claims
    assert "Among 13 entities with EUR orders" in claim.text
    assert "'Orion Datentechnik GmbH'" in claim.text
    assert "EUR 197,500.00" in claim.text
    assert is_supported(
        claim, {n.id: n for n in graph.nodes}, graph, BUSINESS_CLAIM_SHAPES
    )


def test_superlative_without_currency_refuses(graph: KnowledgeGraph) -> None:
    answer = reason("Which entity has the highest total order value?", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    # The refusal names the incomparable currencies — an honest, useful no.
    for currency in ("EUR", "USD", "GBP"):
        assert currency in answer.refusal


def test_superlative_unknown_currency_refuses(graph: KnowledgeGraph) -> None:
    answer = reason("Highest total order value in JPY?", graph)
    assert not answer.is_grounded


# --- dispatch boundary ----------------------------------------------------------


def test_non_multi_step_refuses(graph: KnowledgeGraph) -> None:
    answer = reason("Tell me about Müller Logistik.", graph)
    assert not answer.is_grounded
    assert answer.refusal == NOT_MULTI_REFUSAL


# --- adversarial: the new verifier shapes can fail -------------------------------


def test_verifier_rejects_wrong_superlative_winner(graph: KnowledgeGraph) -> None:
    """A fabricated 'Müller is highest' claim is caught by graph recomputation."""
    honest = reason("Highest total order value in EUR?", graph)
    (real,) = honest.claims
    lie = Claim(
        text=real.text.replace("Orion Datentechnik GmbH", "Mueller Logistik Gmbh"),
        support=real.support,
    )
    assert not is_supported(
        lie, {n.id: n for n in graph.nodes}, graph, BUSINESS_CLAIM_SHAPES
    )


def test_verifier_rejects_flipped_compare_direction(graph: KnowledgeGraph) -> None:
    answer = reason("Compare Müller Logistik and Nordwind Logistik totals.", graph)
    conclusion = answer.claims[-1]
    flipped = Claim(
        text=conclusion.text.replace("Nordwind Logistik GmbH", "TMP")
        .replace("Mueller Logistik Gmbh", "Nordwind Logistik GmbH")
        .replace("TMP", "Mueller Logistik Gmbh"),
        support=conclusion.support,
    )
    assert not is_supported(
        flipped, {n.id: n for n in graph.nodes}, graph, BUSINESS_CLAIM_SHAPES
    )


def test_verifier_rejects_wrong_entity_count(graph: KnowledgeGraph) -> None:
    honest = reason("Highest total order value in EUR?", graph)
    (real,) = honest.claims
    lie = Claim(text=real.text.replace("Among 13", "Among 12"), support=real.support)
    assert not is_supported(
        lie, {n.id: n for n in graph.nodes}, graph, BUSINESS_CLAIM_SHAPES
    )
