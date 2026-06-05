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
    Locator,
    Origin,
    answer,
)


def _rec(rid: str, row: int, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=rid,
        origin=Origin(
            source="demo.csv",
            locator=Locator.table_row("demo", row),
            ingested_at="2026-06-05",
        ),
        text=text,
    )


_R1 = _rec("r1", 1, "Widget costs $10.")
_R2 = _rec("r2", 2, "Gadget costs $25.")
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
    # The rendered provenance shows the source and the in-source locator.
    assert "demo.csv" in rendered
    assert "row 1" in rendered


def test_render_refusal() -> None:
    rendered = answer("Who is the CEO?", _KB).render()
    assert REFUSAL_MESSAGE in rendered


def test_answer_is_an_answer() -> None:
    assert isinstance(answer("widget cost", _KB), Answer)


def test_locator_is_modality_agnostic() -> None:
    """Forward-compat: a document span fits the SAME Locator type as a table row.

    This is the deliberate Unit 2 hook (page/line/chunk) proven in code now — the
    origin's locator field never has to be restructured for a new modality.
    """
    table_row = Locator.table_row("I_Customer", 12)
    doc_span = Locator(
        kind="doc-span", parts=(("page", "3"), ("line", "10"), ("chunk", "2"))
    )
    # Both are the same type, render uniformly, and need no kind-specific branch.
    assert isinstance(doc_span, Locator)
    assert table_row.render() == "table I_Customer, row 12"
    assert doc_span.render() == "page 3, line 10, chunk 2"
    # An EvidenceRecord accepts either without change.
    rec = EvidenceRecord(
        id="doc:1",
        origin=Origin(source="runbook.md", locator=doc_span, ingested_at="2026-06-05"),
        text="restart the service",
    )
    assert "page 3" in rec.source
