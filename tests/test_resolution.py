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
    confirm_name_match,
    corpus_generic_tokens,
    normalize,
    significant_tokens,
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


# --- the stem gate: confirm_name_match / corpus_generic_tokens (spec 0070) -----

_SUFFIX_COHORT = [
    "Granite Logistik GmbH",
    "Pyrite Logistik GmbH",
    "Cobalt Logistik GmbH",
    "Basalt Logistik GmbH",
]


def test_gate_vetoes_the_generic_suffix_over_merge() -> None:
    """The headline cure: a shared generic suffix no longer confirms a merge."""
    generic = corpus_generic_tokens(_SUFFIX_COHORT)
    assert "logistik" in generic  # corpus-derived: it spans distinct firms
    assert confirm_name_match(_SUFFIX_COHORT[0], _SUFFIX_COHORT[1], generic) is None


def test_gate_cures_a_multi_token_generic_suffix() -> None:
    """A two-word boilerplate suffix must not defeat the gate (the fixpoint in
    corpus_generic_tokens flags BOTH suffix words, not just the strongest)."""
    cohort = [f"{head} Trade Logistik GmbH" for head in ("Granite", "Pyrite", "Cobalt")]
    generic = corpus_generic_tokens(cohort)
    assert {"trade", "logistik"} <= generic
    assert confirm_name_match(cohort[0], cohort[1], generic) is None


def test_gate_rescues_a_single_typo_in_a_short_head() -> None:
    """A one-edit typo in a short head under a corpus-generic suffix still merges:
    stripping the suffix would drop the bare-stem ratio below threshold, so the
    edit-distance fallback carries it ('stein'~'stien' = 2 edits)."""
    cohort = [*_SUFFIX_COHORT, "Stein Logistik GmbH", "Stien Logistik GmbH"]
    generic = corpus_generic_tokens(cohort)
    assert confirm_name_match("Stein Logistik GmbH", "Stien Logistik GmbH", generic)
    # ...but two genuinely different heads still veto.
    assert (
        confirm_name_match("Granite Logistik GmbH", "Pyrite Logistik GmbH", generic)
        is None
    )


def test_significant_tokens_drop_punctuated_legal_letters() -> None:
    """'G.m.b.H' / 'A/S' abbreviate to single letters that must not pollute a
    distinctive stem (so 'Nordwind G.m.b.H' still matches 'Nordwind Log GmbH')."""
    assert significant_tokens("Nordwind G.m.b.H") == ["nordwind"]
    assert significant_tokens("Nordic Timber A/S") == ["nordic", "timber"]


def test_corpus_genericness_keeps_a_token_repeated_across_one_firm() -> None:
    """The naive-document-frequency trap avoided: 'bayerische' repeats across one
    firm's duplicate records but must NOT be marked generic (else the cluster
    splits) — removing it leaves the records still similar, so it spans one firm."""
    names = ["Bayerische Stahlwerke AG"] * 3 + ["Bayersche Stahlwerke AG"]
    generic = corpus_generic_tokens(names)
    assert "bayerische" not in generic
    assert "stahlwerke" not in generic


def test_corpus_genericness_is_permutation_invariant() -> None:
    """Order-independence (the greedy distinct-firm count is otherwise sensitive to
    a 'star' similarity structure among the reduced names)."""
    star = ["k" * 20] + ["k" * 20 + leaf * 6 for leaf in "pqr"]
    signatures = {
        corpus_generic_tokens(perm) for perm in (star, star[::-1], sorted(star))
    }
    assert len(signatures) == 1
