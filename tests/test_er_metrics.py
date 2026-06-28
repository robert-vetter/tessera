"""ER precision/recall, measured (spec 0062).

There is no ER battery in the eval — the three batteries score answer-path
coverage/faithfulness, not merge correctness. Per CLAUDE.md principle 3
("nothing is done until its metric effect is known"), this IS the ER metric: a
labeled pair set (truly-same vs truly-distinct firms/services) scored by each
matcher, so the embedding regime's effect on recall AND precision is a measured
fact, pinned here so drift is loud — **not** a new gated CI floor (faithfulness
stays the only hard one).

The measured table (asserted below):

    matcher              precision   recall
    difflib (gated)         1.00      0.50    misses checkout/notif; NO over-merge
    stem-embedding          1.00      1.00    bridges abbreviation + synonym stems
    union                   1.00      1.00    recall AND precision closed

Milestone 8 (spec 0070 / ADR 0018) **cured** the generic-suffix over-merge that
Milestone 7 recorded as difflib's residual: the deterministic ``difflib`` pass is
now *stem-gated* — a character match is confirmed only when the names share a
distinctive (non-generic) signal, so Granite/Pyrite (0.865) and Cobalt/Basalt
(0.889) no longer merge. Difflib precision moved 0.50 → 1.00 and the union 0.67 →
1.00, with recall unchanged (the abbreviation/synonym misses are still the
embedding's job). The matcher here applies the *same* gate the engine's
``resolve_entities`` runs, over this labelled corpus.

The residual difflib's over-merge left — name-only ER's floor, two distinct firms
with character-identical names — is **closed in Milestone 9** by multi-field ER (name
+ address, spec 0073/0074, ADR 0019): the address signal splits two same-named firms
at different postal codes. This name-pair set stays a *name-matcher* measurement (it
has no addresses); the multi-field cure is measured on graphs with addresses in
``tests/test_multifield_er.py``, ``tests/test_scale.py``, and
``tests/test_m9_multifield_close.py``. The remaining floor is two distinct firms with
the same name **and** the same address — a registration/tax key, named future work.

The stub embedder is a keyword-axis toy: it proves a model that places synonym
stems close achieves the measured recall WITHOUT adding false merges. The real
model's recall is the recorded online run (spec 0066), not this test.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from tessera.er_semantic import propose_semantic_resolutions
from tessera.platform.vectors import InMemoryVectorStore
from tessera.resolution import (
    DEFAULT_RESOLUTION_THRESHOLD,
    confirm_name_match,
    corpus_generic_tokens,
    similarity,
)

Matcher = Callable[[str, str], bool]

# --- the labeled pair set (each negative/positive annotated with its difflib) ---

SHOULD_MERGE = [  # truly the same entity
    ("checkout-service", "checkout-svc"),  # difflib 0.846 — baseline MISS (recall gap)
    (
        "notifications-service",
        "notif-svc",
    ),  # difflib 0.429 — baseline MISS (recall gap)
    ("search-service", "search-servce"),  # difflib 0.960 — baseline HIT (typo)
    ("payments-service", "Payments Service"),  # difflib 1.000 — baseline HIT (case)
]
SHOULD_NOT_MERGE = [  # truly distinct entities
    ("Granite Logistik GmbH", "Pyrite Logistik GmbH"),  # 0.865 — was over-merge, GATED
    ("Cobalt Logistik GmbH", "Basalt Logistik GmbH"),  # 0.889 — was over-merge, GATED
    ("Müller Logistik GmbH", "Nordwind Logistik GmbH"),  # difflib 0.667 — apart
    ("checkout-service", "payments-service"),  # difflib 0.600 — apart
]


class StubStemEmbeddings:
    """Keyword-axis embedder over stems (no network). A stem fires every axis
    whose keyword is a substring of it, so a synonym stem (``notif`` vs
    ``notifications``) shares an axis while distinct stems stay orthogonal."""

    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0 if any(k in t.lower() for k in axis) else 0.0 for axis in self._axes]
            for t in texts
        ]


# One axis per distinctive concept; "notif" is a substring of "notifications".
_AXES = [
    ("checkout",),
    ("notif",),
    ("search",),
    ("payments",),
    ("granite",),
    ("pyrite",),
    ("cobalt",),
    ("basalt",),
    ("mueller", "muller"),
    ("nordwind",),
]


def _all_names() -> list[str]:
    seen: dict[str, None] = {}  # ordered, de-duplicated
    for a, b in SHOULD_MERGE + SHOULD_NOT_MERGE:
        seen.setdefault(a, None)
        seen.setdefault(b, None)
    return list(seen)


def _precision_recall(
    matcher: Matcher,
) -> tuple[float, float]:
    """Precision/recall of a pair matcher over the labeled set."""
    tp = sum(1 for a, b in SHOULD_MERGE if matcher(a, b))
    fn = len(SHOULD_MERGE) - tp
    fp = sum(1 for a, b in SHOULD_NOT_MERGE if matcher(a, b))
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return precision, recall


# The gate's corpus stoplist over this labelled set — the same derivation
# ``KnowledgeGraph.resolve_entities`` runs (spec 0070). "logistik" spans the
# distinct Logistik firms here, so it is generic and the cohort splits.
_CORPUS_GENERIC = corpus_generic_tokens(_all_names())


def _difflib_matcher(a: str, b: str) -> bool:
    """The deterministic pass as the engine now runs it: a character match at/above
    the threshold, *gated* on a shared distinctive signal (spec 0070 / ADR 0018)."""
    return (
        similarity(a, b) >= DEFAULT_RESOLUTION_THRESHOLD
        and confirm_name_match(a, b, _CORPUS_GENERIC) is not None
    )


def _embedding_merges() -> set[frozenset[str]]:
    """The pairs the stem-embedding regime proposes over the labeled corpus
    (name used as its own node id)."""
    named = [(name, name) for name in _all_names()]
    proposals = propose_semantic_resolutions(
        named, StubStemEmbeddings(_AXES), InMemoryVectorStore()
    )
    return {frozenset({r.node_a, r.node_b}) for r in proposals}


def _embedding_matcher() -> Matcher:
    merges = _embedding_merges()
    return lambda a, b: frozenset({a, b}) in merges


def _union_matcher() -> Matcher:
    embedding = _embedding_matcher()
    return lambda a, b: _difflib_matcher(a, b) or embedding(a, b)


# --- the measured numbers, pinned --------------------------------------------


def test_gated_difflib_has_a_recall_gap_but_no_precision_gap() -> None:
    precision, recall = _precision_recall(_difflib_matcher)
    # 2/4 positives caught (search-servce, Payments Service); the abbreviation and
    # synonym misses (checkout, notif) remain — that is the embedding's job.
    assert recall == pytest.approx(0.50)
    # The stem gate removed both generic-suffix over-merges (Granite/Pyrite,
    # Cobalt/Basalt), so precision is now perfect — the Milestone-8 cure.
    assert precision == pytest.approx(1.00)


def test_stem_embedding_regime_is_precise_and_higher_recall() -> None:
    precision, recall = _precision_recall(_embedding_matcher())
    # The regime bridges both abbreviation (checkout) and synonym (notif) stems
    # and adds NO false merge — the generic-suffix firms reduce to distinct stems.
    assert precision == pytest.approx(1.00)
    assert recall == pytest.approx(1.00)


def test_union_closes_recall_and_precision() -> None:
    precision, recall = _precision_recall(_union_matcher())
    # Recall fully closed by the embedding (the headline ER win)...
    assert recall == pytest.approx(1.00)
    # ...and precision is now also perfect: the stem gate cured difflib's
    # over-merges, and the embedding adds none, so the union has no false merge.
    assert precision == pytest.approx(1.00)


def test_embedding_adds_exactly_the_two_recall_misses() -> None:
    embedding = _embedding_matcher()
    # The two pairs difflib missed are exactly the ones the embedding regime adds.
    assert embedding("checkout-service", "checkout-svc")
    assert embedding("notifications-service", "notif-svc")
    assert not _difflib_matcher("checkout-service", "checkout-svc")
    assert not _difflib_matcher("notifications-service", "notif-svc")


def test_the_generic_suffix_over_merge_is_cured() -> None:
    """The former residual, now closed (spec 0070 / ADR 0018): the stem gate makes
    the deterministic pass produce ZERO false merges over the labelled set — the
    generic-suffix collisions Milestone 7 could not remove additively are gone."""
    difflib_false_merges = {
        frozenset({a, b}) for a, b in SHOULD_NOT_MERGE if _difflib_matcher(a, b)
    }
    assert difflib_false_merges == set()
    # The embedding regime still over-merges nothing either — the union stays clean.
    embedding = _embedding_matcher()
    assert not any(embedding(a, b) for a, b in SHOULD_NOT_MERGE)
    # The cure is a gate, not a similarity miss: the bare ratio WOULD have merged
    # the generic-suffix cohort (both pairs clear 0.85), the gate vetoes them.
    for a, b in [
        ("Granite Logistik GmbH", "Pyrite Logistik GmbH"),
        ("Cobalt Logistik GmbH", "Basalt Logistik GmbH"),
    ]:
        assert similarity(a, b) >= DEFAULT_RESOLUTION_THRESHOLD
        assert not _difflib_matcher(a, b)
