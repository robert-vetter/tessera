"""Tests for lexical retrieval and the retrieve-driven answer.

These pin the behaviour the coverage metric will later measure: relevant evidence
ranks above irrelevant, retrieval spans both modalities, an unsupported question
is refused, and every surfaced claim carries provenance.
"""

from __future__ import annotations

from tessera.business.knowledge import DEMO_KB
from tessera.grounding import (
    REFUSAL_MESSAGE,
    EvidenceRecord,
    KnowledgeBase,
    Locator,
    Origin,
)
from tessera.retrieval import answer, retrieve


def _rec(rid: str, text: str) -> EvidenceRecord:
    origin = Origin("test.csv", Locator.table_row("T", 1), "2026-06-05")
    return EvidenceRecord(id=rid, origin=origin, text=text)


def _kb(*texts: str) -> KnowledgeBase:
    return KnowledgeBase(records=tuple(_rec(f"r{i}", t) for i, t in enumerate(texts)))


def test_retrieve_ranks_relevant_above_irrelevant() -> None:
    kb = _kb(
        "Acme Corp annual contract renewal in August",
        "Unrelated note about widget pricing",
        "Globex shipping schedule for Q3",
    )
    hits = retrieve("When does Acme's contract renew?", kb, k=3)
    assert hits
    assert hits[0][0].text.startswith("Acme Corp")


def test_retrieve_is_deterministic() -> None:
    first = retrieve("Müller Logistik sales orders", DEMO_KB)
    second = retrieve("Müller Logistik sales orders", DEMO_KB)
    assert [r.id for r, _ in first] == [r.id for r, _ in second]


def test_retrieve_empty_when_no_overlap() -> None:
    kb = _kb("Acme Corp contract", "Globex invoice")
    assert retrieve("What colour is the sky?", kb) == []


def test_answer_surfaces_evidence_with_provenance() -> None:
    result = answer(
        "When does Acme's contract renew?",
        _kb("Acme Corp contract auto-renews each August", "irrelevant note"),
    )
    assert result.is_grounded
    assert result.claims
    for claim in result.claims:  # provenance is mandatory for every surfaced claim
        assert claim.support
        assert all(rec.origin.source for rec in claim.support)


def test_answer_refuses_when_no_relevant_evidence() -> None:
    result = answer("What colour is the sky?", DEMO_KB)
    assert not result.is_grounded
    assert result.claims == ()
    assert result.refusal == REFUSAL_MESSAGE


def test_orders_question_returns_salt_rows() -> None:
    result = answer("What are Müller Logistik's sales orders?", DEMO_KB)
    assert result.is_grounded
    sources = {rec.origin.source for c in result.claims for rec in c.support}
    assert any(s.startswith("salt_synthetic/") for s in sources)


def test_renewal_question_returns_the_actual_renewal_clause() -> None:
    """Cross-source into a document: the renewal section of the agreement is the
    *top* result, with doc-span provenance, carrying the actual auto-renewal clause.

    History (spec 0082, ADR 0021): this assertion was once relaxed to a top-2
    invariant because the section *heading* ("## 2. Term and renewal") was a
    standalone chunk that scored within ~0.05% of its own clause on BM25, so their
    order flipped with tiny corpus-size changes (the Milestone-10 disambiguation
    firms shifted ``avgdl`` by a hair). Milestone 11 fixed the root cause at the
    chunking layer — a heading now leads its section's content chunk instead of
    competing with it — so the renewal section is a stable rank-1 again, and the
    strict assertion is restored.
    """
    result = answer(
        "What are the renewal and termination terms of the service agreement?",
        DEMO_KB,
    )
    assert result.is_grounded
    top = result.claims[0].support[0]
    # The top result is the renewal section of the MSA, with doc-span provenance,
    # and it carries the auto-renewal clause itself (no heading-only chunk competes).
    assert top.origin.source.endswith("mueller_logistik_msa.md")
    assert top.origin.locator.kind == "doc-span"
    assert "auto-renews" in top.text
