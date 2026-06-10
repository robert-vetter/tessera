"""The service-ownership path (spec 0036): the coverage loop, closed honestly.

The measured Phase 3 miss — "who is on call for notifications-service?"
could not surface the `notif-svc` on-call row — must now be answered from
the alias-resolved entity, while everything the mechanism does NOT fix
(undeclared abbreviations, unknown services) keeps refusing or missing in
the open.
"""

from __future__ import annotations

import pytest

from tessera.devex.knowledge import build_devex_graph
from tessera.devex.ownership import NO_SERVICE_REFUSAL, find_service, service_lookup
from tessera.graph import KnowledgeGraph


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_devex_graph()


def test_notifications_oncall_surfaces_catalog_and_oncall_rows(
    graph: KnowledgeGraph,
) -> None:
    """The closed loop: catalog row AND the alias-resolved on-call row, each
    a verbatim cited snippet — exactly what gold case 04 expects."""
    answer = service_lookup("Who is on call for notifications-service?", graph)
    assert answer.is_grounded
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert {"Component:SVC-NOTIF", "Owner:notif-svc"} <= cited
    rendered = answer.render()
    assert "Comms" in rendered and "Aiko Tanaka" in rendered


def test_question_can_name_the_service_by_its_alias(graph: KnowledgeGraph) -> None:
    answer = service_lookup("Who is on call for notif-svc?", graph)
    assert answer.is_grounded
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert "Component:SVC-NOTIF" in cited


def test_catalog_row_comes_first(graph: KnowledgeGraph) -> None:
    """The canonical identity leads the answer; on-call rows follow."""
    answer = service_lookup("Who is on call for payments-service?", graph)
    cited_order = [claim.support[0].id for claim in answer.claims]
    assert cited_order[0] == "Component:SVC-PAY"
    assert "Owner:Payments Service" in cited_order[1:]


def test_undeclared_abbreviation_yields_an_honest_partial_answer(
    graph: KnowledgeGraph,
) -> None:
    """Asking by the undeclared `checkout-svc` form reaches only the on-call
    row — the unresolved near-miss stays visible, not papered over."""
    answer = service_lookup("Who is on call for checkout-svc?", graph)
    assert answer.is_grounded
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert cited == {"Owner:checkout-svc"}


def test_no_service_named_refuses(graph: KnowledgeGraph) -> None:
    answer = service_lookup("Who is on call for the espresso machine?", graph)
    assert not answer.is_grounded
    assert answer.refusal == NO_SERVICE_REFUSAL


def test_tie_between_distinct_services_refuses(graph: KnowledgeGraph) -> None:
    """Equal-strength references to two different entities are ambiguous —
    refused with both candidates named, never guessed (the resolve_entity
    discipline). 'payments-service' and 'checkout-service' normalize to the
    same length, so naming both is a true tie."""
    tie = find_service("payments-service or checkout-service?", graph)
    assert tie.status == "ambiguous"
    assert len(tie.candidates) == 2
    answer = service_lookup("payments-service or checkout-service?", graph)
    assert not answer.is_grounded
    assert (
        answer.refusal is not None and "Ambiguous service reference" in answer.refusal
    )


def test_unequal_references_pick_the_most_specific(graph: KnowledgeGraph) -> None:
    # "payments-service" (15 normalized chars) vs "auth-service" (11):
    # the longer, more specific reference wins — not a tie, not a guess.
    longer = find_service("payments-service or auth-service?", graph)
    assert longer.status == "ok"
    assert "Component:SVC-PAY" in longer.cluster
