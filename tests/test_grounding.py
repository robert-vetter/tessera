"""Tests for the grounding engine.

These assert the project's principles, not just output shape: provenance is
mandatory, the system can decline, and it never cites evidence it doesn't have.
"""

import pytest

from tessera.grounding import (
    REFUSAL_MESSAGE,
    Answer,
    Claim,
    EvidenceRecord,
    Fact,
    KnowledgeBase,
    answer,
)

_R1 = EvidenceRecord(id="r1", source="demo.csv, row 1", text="Widget costs $10.")
_R2 = EvidenceRecord(id="r2", source="demo.csv, row 2", text="Gadget costs $25.")
_KB = KnowledgeBase(
    records=(_R1, _R2),
    facts=(
        Fact(keywords=("widget", "cost"), claim=Claim("A widget costs $10.", (_R1,))),
        Fact(keywords=("gadget", "cost"), claim=Claim("A gadget costs $25.", (_R2,))),
    ),
)


def test_claim_requires_provenance() -> None:
    """A claim with no supporting evidence is unrepresentable."""
    with pytest.raises(ValueError):
        Claim(text="ungrounded", support=())


def test_grounded_answer_has_provenance() -> None:
    result = answer("What does a widget cost?", _KB)
    assert result.is_grounded
    assert result.claims
    # Every claim carries at least one piece of supporting evidence.
    assert all(claim.support for claim in result.claims)


def test_answer_only_cites_known_records() -> None:
    """An answer never cites evidence outside the knowledge base."""
    result = answer("What does a widget or gadget cost?", _KB)
    cited = {record for claim in result.claims for record in claim.support}
    assert cited
    assert cited <= set(_KB.records)


def test_refusal_when_no_evidence() -> None:
    result = answer("Who is the CEO?", _KB)
    assert not result.is_grounded
    assert result.claims == ()
    assert result.refusal == REFUSAL_MESSAGE


def test_render_shows_claims_and_sources() -> None:
    rendered = answer("What does a widget cost?", _KB).render()
    assert "A widget costs $10." in rendered
    assert "demo.csv, row 1" in rendered


def test_render_refusal() -> None:
    rendered = answer("Who is the CEO?", _KB).render()
    assert REFUSAL_MESSAGE in rendered


def test_answer_is_an_answer() -> None:
    assert isinstance(answer("widget cost", _KB), Answer)
