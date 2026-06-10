"""The shared-fragment verifier shape: generic, and provably able to fail.

This is ADR 0008's one sanctioned verifier delta, so it gets the ADR 0005
treatment: fixtures here are deliberately vertical-free (no DevEx, no
business vocabulary) to demonstrate the shape's neutrality, and every way a
fabricated cross-source claim could cheat is shown to be caught.
"""

from __future__ import annotations

from tessera.eval.metrics import is_supported
from tessera.grounding import Claim, EvidenceRecord, Locator, Origin


def _record(record_id: str, source: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=record_id,
        origin=Origin(
            source=source,
            locator=Locator(kind="test-span", parts=(("part", "1"),)),
            ingested_at="2026-06-10",
        ),
        text=text,
    )


A = _record("a:1", "alpha.txt", "the omen phrase shows up here")
B = _record("b:1", "beta.txt", "and the omen phrase shows up there")
C = _record("c:1", "gamma.txt", "entirely unrelated content")


def _claim(text: str, *support: EvidenceRecord) -> Claim:
    return Claim(text=text, support=tuple(support))


def test_true_shared_fragment_is_supported() -> None:
    claim = _claim(
        "Recurring: \"omen phrase\" appears in 'alpha.txt' and 'beta.txt'.", A, B
    )
    assert is_supported(claim, {})


def test_fragment_absent_from_one_citation_is_caught() -> None:
    claim = _claim(
        "Recurring: \"omen phrase\" appears in 'alpha.txt' and 'gamma.txt'.", A, C
    )
    assert not is_supported(claim, {})


def test_named_source_not_among_citations_is_caught() -> None:
    claim = _claim(
        "Recurring: \"omen phrase\" appears in 'alpha.txt' and 'delta.txt'.", A, B
    )
    assert not is_supported(claim, {})


def test_cited_record_from_unnamed_source_is_caught() -> None:
    claim = _claim(
        "Recurring: \"omen phrase\" appears in 'alpha.txt' and 'beta.txt'.", A, B, C
    )
    assert not is_supported(claim, {})


def test_single_citation_is_caught() -> None:
    claim = _claim("Recurring: \"omen phrase\" appears in 'alpha.txt'.", A)
    assert not is_supported(claim, {})


def test_single_quotes_inside_fragment_do_not_masquerade_as_sources() -> None:
    """Sources parse from the tail after 'appears in' only — a fragment like
    ImportError: cannot import name 'x' must not add phantom sources."""
    rec_a = _record("a:2", "alpha.txt", "ERROR cannot import name 'x' from 'y.z'")
    rec_b = _record("b:2", "beta.txt", "seen: cannot import name 'x' from 'y.z'")
    claim = _claim(
        "Recurring: \"cannot import name 'x' from 'y.z'\" appears in "
        "'alpha.txt' and 'beta.txt'.",
        rec_a,
        rec_b,
    )
    assert is_supported(claim, {})


def test_grammar_does_not_hijack_ordinary_claims() -> None:
    """A claim without the grammar still verifies by snippet containment."""
    snippet = _claim("the omen phrase shows up here", A)
    assert is_supported(snippet, {})
