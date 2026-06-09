"""Tests for the deterministic name matcher.

The threshold must merge the known typo/umlaut variants while keeping distinct
firms that merely share a generic token apart — the precision/recall line the ER
layer lives on.
"""

from __future__ import annotations

from tessera.resolution import (
    DEFAULT_RESOLUTION_THRESHOLD as T,
)
from tessera.resolution import (
    normalize,
    similarity,
)


def test_normalize_folds_umlauts_and_case() -> None:
    assert normalize("Müller Logistik GmbH") == "muellerlogistikgmbh"
    assert normalize("Mueller Logistik Gmbh") == "muellerlogistikgmbh"


def test_similarity_is_symmetric_and_bounded() -> None:
    s = similarity("Bayersche Stahlwerke AG", "Bayerische Stahlwerke AG")
    assert 0.0 <= s <= 1.0
    assert s == similarity("Bayerische Stahlwerke AG", "Bayersche Stahlwerke AG")


def test_variants_merge_above_threshold() -> None:
    assert similarity("Müller Logistik GmbH", "Mueller Logistik Gmbh") >= T
    assert similarity("Bayeriche Stahlwerke AG.", "Bayerische Stahlwerke AG") >= T
    assert similarity("Bayersche Stahlwerke AG", "Bayerische Stahlwerke AG") >= T


def test_distinct_firms_sharing_a_token_stay_below_threshold() -> None:
    # Both end in "Logistik GmbH" but are different companies — must NOT merge.
    assert similarity("Müller Logistik GmbH", "Nordwind Logistik GmbH") < T


def test_empty_names_score_zero() -> None:
    assert similarity("", "anything") == 0.0
