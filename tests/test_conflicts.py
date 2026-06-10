"""Conflicting evidence is surfaced with both sides cited — never silently mixed."""

import pytest

from tessera.composition import compose
from tessera.conflicts import find_renewal_conflict, renewal_date_of
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph
from tessera.grounding import Claim, EvidenceRecord, Locator, Origin
from tessera.knowledge import build_demo_graph


def _clause(rid: str, source: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=rid,
        origin=Origin(
            source=source,
            locator=Locator.doc_span(1, 3, 1),
            ingested_at="2026-06-05",
        ),
        text=text,
    )


_MSA = _clause(
    "msa:chunk1",
    "business_docs/msa.md",
    "the Agreement auto-renews annually on 1 August.",
)
_AMENDMENT = _clause(
    "amend:chunk1",
    "business_docs/amendment.md",
    "the Agreement auto-renews annually on 1 February, aligning fiscal years.",
)
_UNRELATED = _clause(
    "other:chunk1", "business_docs/other.md", "Payment within 30 days."
)


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_demo_graph()


# --- detection -------------------------------------------------------------------


def test_renewal_date_extraction() -> None:
    assert renewal_date_of(_MSA) == "1 August"
    assert renewal_date_of(_AMENDMENT) == "1 February"
    assert renewal_date_of(_UNRELATED) is None


def test_conflict_found_and_cites_both_sides() -> None:
    conflict = find_renewal_conflict([_MSA, _AMENDMENT, _UNRELATED])
    assert conflict is not None
    assert "1 August" in conflict.text and "1 February" in conflict.text
    assert "No single renewal date can be asserted" in conflict.text
    assert set(conflict.support) == {_MSA, _AMENDMENT}


def test_no_conflict_when_dates_agree() -> None:
    assert find_renewal_conflict([_MSA, _UNRELATED]) is None
    assert find_renewal_conflict([]) is None


# --- end to end through composition ----------------------------------------------


def test_compose_surfaces_mueller_conflict(graph: KnowledgeGraph) -> None:
    answer = compose("When does Müller Logistik's agreement renew?", graph)
    assert answer.is_grounded
    rendered = answer.render()
    assert "disagree on the renewal date" in rendered
    assert "1 August" in rendered and "1 February" in rendered
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert {"mueller_logistik_msa:chunk6", "mueller_logistik_amendment:chunk4"} <= cited


def test_conflict_claim_passes_faithfulness(graph: KnowledgeGraph) -> None:
    answer = compose("When does Müller Logistik's agreement renew?", graph)
    nodes = {n.id: n for n in graph.nodes}
    conflict_claims = [
        c for c in answer.claims if "disagree on the renewal date" in c.text
    ]
    assert len(conflict_claims) == 1
    assert is_supported(conflict_claims[0], nodes, graph)


# --- adversarial: the conflict shape can fail -------------------------------------


def test_verifier_rejects_conflict_with_agreeing_citations() -> None:
    """A 'conflict' claim whose citations actually agree is unfaithful."""
    lie = Claim(
        text=(
            "Conflict: the cited documents disagree on the renewal date — "
            "'1 August' (a.md); '1 February' (b.md). No single renewal date "
            "can be asserted."
        ),
        support=(_MSA, _UNRELATED),  # only ONE date-stating clause cited
    )
    assert not is_supported(lie, {})


def test_verifier_rejects_conflict_with_uncited_value() -> None:
    """Quoted values must be exactly the dates the cited clauses state."""
    lie = Claim(
        text=(
            "Conflict: the cited documents disagree on the renewal date — "
            "'1 March' (a.md); '1 February' (b.md). No single renewal date "
            "can be asserted."
        ),
        support=(_MSA, _AMENDMENT),  # these state August/February, not March
    )
    assert not is_supported(lie, {})
