"""Tests for the grounding data model.

These assert the project's principles at the type level: provenance is mandatory
(a claim cannot exist without supporting evidence), the origin is modality-
agnostic and forward-compatible, and the rendered answer shows where each claim
came from. Retrieval and answering live in :mod:`tessera.retrieval`.
"""

import pytest

from tessera.grounding import (
    REFUSAL_MESSAGE,
    Answer,
    Claim,
    EvidenceRecord,
    KnowledgeBase,
    Locator,
    Origin,
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


def test_claim_requires_provenance() -> None:
    """A claim with no supporting evidence is unrepresentable."""
    with pytest.raises(ValueError):
        Claim(text="ungrounded", support=())


def test_evidence_record_source_includes_locator() -> None:
    rec = _rec("r1", 1, "Widget costs $10.")
    assert "demo.csv" in rec.source
    assert "row 1" in rec.source


def test_locator_is_modality_agnostic() -> None:
    """Forward-compat: a document span fits the SAME Locator type as a table row,
    so the origin never has to be restructured for a new modality."""
    table_row = Locator.table_row("I_Customer", 12)
    doc_span = Locator.doc_span(10, 14, 2)
    assert isinstance(doc_span, Locator)
    assert table_row.render() == "table I_Customer, row 12"
    assert doc_span.render() == "lines 10-14, chunk 2"
    rec = EvidenceRecord(
        id="doc:1",
        origin=Origin(source="runbook.md", locator=doc_span, ingested_at="2026-06-05"),
        text="restart the service",
    )
    assert "lines 10-14" in rec.source


def test_answer_render_shows_claim_and_source() -> None:
    rec = _rec("r1", 1, "Widget costs $10.")
    answer = Answer(
        question="What does a widget cost?",
        claims=(Claim("Widget costs $10.", (rec,)),),
        refusal=None,
    )
    out = answer.render()
    assert "Widget costs $10." in out
    assert "demo.csv" in out  # provenance shows the source and locator
    assert "row 1" in out


def test_answer_render_refusal() -> None:
    answer = Answer(question="Who is the CEO?", claims=(), refusal=REFUSAL_MESSAGE)
    assert REFUSAL_MESSAGE in answer.render()


def test_is_grounded() -> None:
    rec = _rec("r1", 1, "Widget costs $10.")
    assert Answer("q", (Claim("c", (rec,)),), None).is_grounded
    assert not Answer("q", (), REFUSAL_MESSAGE).is_grounded


def test_knowledge_base_holds_records() -> None:
    kb = KnowledgeBase(records=(_rec("r1", 1, "x"),))
    assert kb.records
