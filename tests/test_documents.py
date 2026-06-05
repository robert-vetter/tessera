"""Tests for unstructured (document) ingestion.

Beyond the ingestion invariants, two of these encode the requirements that make
the second modality worth having: documents reference customers in *variant*
forms (so linking them to a table row is genuine resolution work, not an exact
match), and they carry information the tables *lack* (so a later cross-source
answer combines two real halves rather than restating one).
"""

from __future__ import annotations

import csv
import re

from tessera.ingestion import Ingester
from tessera.knowledge import DEMO_KB
from tessera.retrieval import answer
from tessera.sources.documents import DATA_DIR, DocumentSource
from tessera.sources.salt import DATA_DIR as SALT_DIR


def _normalize(name: str) -> str:
    folded = (
        name.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return re.sub(r"[^a-z0-9]", "", folded)


def _customer_names() -> set[str]:
    path = SALT_DIR / "I_Customer.csv"
    return {r["CustomerName"] for r in csv.DictReader(path.open(encoding="utf-8"))}


def _corpus_text() -> str:
    return "\n".join(
        (DATA_DIR / name).read_text("utf-8")
        for name in (
            "mueller_logistik_msa.md",
            "bayerische_stahlwerke_terms.md",
            "lumiere_energie_letter.md",
        )
    )


def _salt_text() -> str:
    return "\n".join(p.read_text("utf-8") for p in sorted(SALT_DIR.glob("*.csv")))


def test_source_satisfies_ingester_protocol() -> None:
    assert isinstance(DocumentSource(), Ingester)


def test_every_document_record_has_doc_span_origin() -> None:
    records = DocumentSource().ingest()
    assert records
    for record in records:
        assert record.origin.locator.kind == "doc-span"
        assert record.origin.locator.parts
        assert record.origin.source.startswith("business_docs/")
        assert record.origin.ingested_at
        assert record.text


def test_document_ingestion_is_deterministic() -> None:
    assert DocumentSource().ingest() == DocumentSource().ingest()


def test_document_ids_are_unique() -> None:
    ids = [r.id for r in DocumentSource().ingest()]
    assert len(ids) == len(set(ids))


def test_docs_reference_customers_in_variant_forms() -> None:
    """A document names a customer in a non-canonical form that still *normalizes*
    to a real customer — so the link is real but non-trivial (not exact string)."""
    corpus = _corpus_text()
    names = _customer_names()
    normalized_names = {_normalize(n) for n in names}

    variant = "Mueller Logistik Gmbh"  # address-master spelling of customer 0010000007
    assert variant in corpus
    assert variant not in names  # not the canonical customer-master string
    assert _normalize(variant) in normalized_names  # but resolves to a real customer


def test_at_least_one_doc_needs_real_resolution() -> None:
    """The hard case: a reference that matches no customer-master record even after
    normalization, so only a genuine resolution step (Unit 4) can tie it to a row."""
    corpus = _corpus_text()
    names = _customer_names()
    normalized_names = {_normalize(n) for n in names}

    # The Lumière letter drops the legal form ("SARL"); the generator never drops
    # legal forms, so no customer-master record matches this even normalized.
    hard = "Lumière Énergie"
    assert hard in corpus
    assert hard not in names
    assert _normalize(hard) not in normalized_names  # exact + normalization both fail


def test_documents_add_information_tables_lack() -> None:
    """Documents carry terms the structured tables do not — non-redundant content."""
    corpus = _corpus_text().lower()
    salt = _salt_text().lower()
    for term in ("auto-renews", "volume discount", "quarterly"):
        assert term in corpus
        assert term not in salt


def test_document_grounded_answer_traces_to_doc_span() -> None:
    """A question about the agreement's terms retrieves the document clause, with
    provenance to a specific doc span (file + line range)."""
    result = answer(
        "What are the renewal and termination terms of the service agreement?",
        DEMO_KB,
    )
    assert result.is_grounded
    support = [rec for claim in result.claims for rec in claim.support]
    clause = next(rec for rec in support if "auto-renews" in rec.text)
    assert clause.origin.source.endswith("mueller_logistik_msa.md")
    assert clause.origin.locator.kind == "doc-span"
